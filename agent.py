# agent.py
from langchain_core.messages import HumanMessage, AnyMessage, ToolMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from tools import tool_registry
from langsmith import Client, traceable
from dotenv import load_dotenv
import torch
from typing import TypedDict, Annotated
from datetime import datetime
from langgraph.prebuilt import ToolNode, tools_condition
from evals import helpfulness_eval
import os
import json

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


load_dotenv()

client = Client()

system_instruction = """
You are TravelGenie, a friendly and knowledgeable AI travel assistant in the year 2025. You have access to a knowledge base of travel information. Use this knowledge base to answer the user's questions.

ROLE & PURPOSE:
You help users plan their travel by:
- Recommending personalized travel ideas, flights, hotels, and activities.
- Asking thoughtful and polite clarifying questions to tailor suggestions (e.g., destination, dates, budget, interests).
- Naturally providing real-time data without mentioning tools or APIs.
- Ensuring every response is helpful, concise, and personalized.
- When possible, use the knowledge base to provide more information.

RESPONSE STYLE & TONE:
- Be warm, polite, and professional—like a friendly, smart concierge.
- Use **Markdown tables** to present flights, hotels, or itineraries clearly.
- Say "USD" instead of "$" for all prices.
- NEVER mention tools, or APIs.
- Use RAG Tool only when asked about specific destinations or travel tips.
- If unsure, say "I'm not sure" or "I don’t know," and offer alternatives.
- Always show results for year 2025.

BEHAVIORAL RULES:
1. Always ask for missing key details politely (e.g., dates, number of travelers, budget).
2. Never repeat questions the user has already answered.
3. Use context from previous user messages (destinations, preferences, dates).
4. Provide multiple options whenever possible to encourage user choice.
5. Stay on-topic but friendly and engaging—spark excitement about travel.
6. Avoid technical references (e.g., don't say "using a tool to check").
7. Apologize or explain gently if something cannot be found.
8. Prioritize information found in the knowledge base.

EXAMPLES OF RESPONSES:

User: I want to fly from New York to Los Angeles.  
TravelGenie: Sure! When would you like to travel? Are you looking for a one-way or round-trip flight?

User: Find me a hotel in Paris.  
TravelGenie: Absolutely! What dates will you be in Paris? Do you have a preference for hotel type or price range?

User: What is there to do in Rome?  
TravelGenie: Rome is full of amazing experiences! 🇮🇹 Are you more interested in history, food, art, or something else? I can tailor suggestions to your style.

User: Show me flights from Chicago to London.  
TravelGenie: Of course! Here are a few flight options:

| Airline           | Departure Time | Arrival Time | Price (USD) |
|------------------|----------------|--------------|-------------|
| United Airlines   | 9:00 AM        | 11:00 PM     | 600         |
| American Airlines | 10:00 AM       | 12:00 AM     | 650         |
| British Airways   | 11:00 AM       | 1:00 AM      | 700         |

Let me know if you’d like to filter by airline, number of stops, or flight duration.

User: Show me hotels in Tokyo.  
TravelGenie: Certainly! Here are some hotel options in Tokyo for your selected dates:

| Hotel Name                  | Location           | Price/Night (USD) | Rating | Reviews |
|----------------------------|--------------------|-------------------|--------|---------|
| Tokyo Bay Grand Hotel      | Tokyo Bay Area     | 120               | 8.5    | 1,250   |
| Shinjuku Grand Hotel      | Shinjuku           | 135               | 8.0    | 980     |
CONTEXT-AWARE BEHAVIOR:
- If the user has previously searched for a city or country, carry that into the next suggestion.
- Example: “Since you enjoyed Tokyo last year, would you like to explore Kyoto this time?”

Your goal is not just to provide data—it’s to create an exciting, smooth, and personal travel planning experience. Make every interaction feel like the start of a great adventure.

"""

tools = list(tool_registry.values())
# Initialize LLM with Ollama
llm = ChatOllama(
    model="llama3.1:8b",
    temperature=0.75,
    top_p=0.75,
    max_tokens=512,
    num_gpu=torch.cuda.device_count() if torch.cuda.is_available() else 0,
    name="TravelGenie",
).bind_tools(tools)

# Memory checkpointer
checkpointer = MemorySaver()


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


@traceable(name="ChatbotFunction", tags=["chat", "travelgenie"])
def chatbot(state: State) -> State:
    messages = state["messages"]
    response = llm.invoke(messages)

    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_outputs = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            print(f"Tool call: {tool_name} with args: {tool_args}")

            tool = next(
                (t for t in tools if getattr(t, "name", None) == tool_name), None
            )
            if tool is None:
                raise ValueError(f"Tool '{tool_name}' not found")

            output = tool.invoke(tool_args)
            tool_outputs.append(
                ToolMessage(tool_call_id=tool_call["id"], content=str(output))
            )

        # Re-invoke with tool outputs
        final_response = llm.invoke(messages + [response] + tool_outputs)
        return {"messages": messages + [response] + tool_outputs + [final_response]}

    return {"messages": messages + [response]}


# Build the graph
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.set_entry_point("chatbot")
graph_builder.add_node("tools", ToolNode(tools))
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")


# Compile with memory
graph = graph_builder.compile(checkpointer=checkpointer)


# print(graph.get_graph().draw_mermaid())
# save the graph as PNG
png = graph.get_graph().draw_mermaid_png()
with open("graph2.png", "wb") as f:
    f.write(png)


def invoke_system(system_instruction: str) -> None:
    """Invoke the system with the given instruction."""
    graph.invoke(
        {"messages": [SystemMessage(content=system_instruction)]},
        config={"configurable": {"thread_id": "conversation_1"}},
    )


invoke_system(system_instruction)


# Run agent with memory
def run_agent(query: str, thread_id: str = "conversation_1"):
    user_message = HumanMessage(content=query)
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [user_message]}, config=config)

    messages = result["messages"]
    response = messages[-1].content
    return query, response, messages


# Save the evaluation result with question and answer and evaluation in JSON format


def save_evaluation_result(
    question: str,
    answer: str,
    evaluation: dict,
    filename: str = "evaluation_results.json",
):
    score_raw = evaluation.get("score", None)
    comment = evaluation.get("comment", "")

    # Explicit True check
    if score_raw is True:
        helpfulness = "Yes"
    elif score_raw is False:
        helpfulness = "No"
    else:
        helpfulness = "N/A"

    result = {
        "Question": question.strip(),
        "Answer": answer.strip(),
        "Helpfulness": helpfulness,
        "Comment": comment.strip(),
    }

    if os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.append(result)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    import traceback

    invoke_system(system_instruction)
    print("Welcome to TravelGenie! Type 'exit' to quit.")

    try:
        while True:
            user_query = input("You: ")
            if user_query.lower() == "exit":
                print("Goodbye! Safe travels!")
                break

            print("-" * 40)
            print(f"[{datetime.now().isoformat()}] Query: {user_query}")
            print("-" * 40)

            try:
                # Run the agent and get response
                query, agent_reply, messages = run_agent(user_query)

                # Print response
                print("TravelGenie:", agent_reply, "\n", "-" * 40)
                print("Messages:\n", messages, "\n", "-" * 40)

                # Uncomment to save the conversation and evaluation
                # Evaluate and save result
                # eval_result = helpfulness_eval(
                #     inputs={"question": query}, outputs={"answer": agent_reply}
                # )
                # print("Evaluation Result:", eval_result, "\n", "-" * 40)
                # save_evaluation_result(
                #     question=query,
                #     answer=agent_reply,
                #     evaluation=eval_result,
                #     filename="evaluation_results.csv",
                # )

            except Exception as inner_error:
                print("An error occurred during interaction:\n", str(inner_error))
                traceback.print_exc()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Exiting gracefully.")
    finally:
        print("Session ended. All data saved.")

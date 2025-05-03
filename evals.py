from openevals.llm import create_llm_as_judge
from openevals.prompts import RAG_HELPFULNESS_PROMPT
from langchain_ollama import ChatOllama

# evaluation model
ollama_model = ChatOllama(model="gemma3:12b")

helpfulness_eval = create_llm_as_judge(
    prompt=RAG_HELPFULNESS_PROMPT,
    feedback_key="helpfulness",
    judge=ollama_model,
)

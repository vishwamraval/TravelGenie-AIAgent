# rag_tool.py

from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.tools import tool
import os


def load_pdf_documents(pdf_folder_path: str) -> list[Document]:
    all_docs = []
    for filename in os.listdir(pdf_folder_path):
        if filename.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(pdf_folder_path, filename))
            docs = loader.load()
            all_docs.extend(docs)
    return all_docs


def load_retriever_from_pdfs(pdf_folder_path: str):
    raw_docs = load_pdf_documents(pdf_folder_path)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    docs = text_splitter.split_documents(raw_docs)

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = FAISS.from_documents(docs, embeddings)
    return db.as_retriever()


retriever = load_retriever_from_pdfs("travel_docs")


@tool
def local_rag_tool(query: str) -> str:
    """Search local travel PDFs for destination tips and highlights specifically about India, China, Japan, Australia, Abu Dhabi, Dubai, or Italy.
    args:
        query: str: The query to search for in the local travel PDFs.
    returns:
        str: The top 3 results from the local travel PDFs.
    """
    results = retriever.invoke(query)
    return "\n\n".join([r.page_content for r in results[:3]])


if __name__ == "__main__":
    response = local_rag_tool.invoke("Tell me about the best places to visit in Italy.")
    print(response)

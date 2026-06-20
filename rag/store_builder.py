import os
from typing import List
from langchain_community.document_loaders import PDFPlumberLoader  # Swapped to robust plumber backend
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class ICMRVectorStoreBuilder:
    """
    Handles loading, parsing, chunking, embedding, and persisting 
    the official ICMR-NIN 2024 guidelines into a 100% free, local BGE-backed ChromaDB layer.
    """
    def __init__(
        self, 
        pdf_path: str = "data/DGI_2024.pdf",  # Updated to your active filename format
        db_dir: str = "rag/vector_db"
    ):
        self.pdf_path = pdf_path
        self.db_dir = db_dir
        
        print("Initializing local open-source embedding engine (BAAI/bge-small-en-v1.5)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cpu'}
        )

    def build_database(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> Chroma:
        """Executes the end-to-end text extraction and chunk ingestion pipeline locally via PDFPlumber."""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(
                f"Missing baseline document! Please place the official manual "
                f"at execution path: '{self.pdf_path}'"
            )

        print(f"Reading document metadata from: {self.pdf_path} (Using PDFPlumber)...")
        # PDFPlumber parses text characters independently of vector image blocks to prevent IndexError crashes
        loader = PDFPlumberLoader(self.pdf_path)
        raw_documents = loader.load()
        print(f"Successfully loaded {len(raw_documents)} raw text pages.")

        print("\nExecuting clinical text split strategy...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        split_docs = text_splitter.split_documents(raw_documents)
        print(f"Created {len(split_docs)} semantic text chunks.")

        print(f"\nInitializing and persisting ChromaDB Vector Store at: {self.db_dir}...")
        vector_db = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory=self.db_dir
        )
        
        print("Successfully committed local BGE vector transformations to storage layer!")
        return vector_db

    def get_existing_store(self) -> Chroma:
        """Loads the persisted vector store from disk without rebuilding."""
        if not os.path.exists(self.db_dir) or not os.listdir(self.db_dir):
            raise FileNotFoundError("Vector directory is empty. Run build_database() first.")
        return Chroma(persist_directory=self.db_dir, embedding_function=self.embeddings)

# Note: Keep your ICMRClinicalRetriever class completely untouched below this block!

# --- INDEPENDENT RETRIEVER CLASS SCOPING ---
class ICMRClinicalRetriever:
    """
    Exposes an operational semantic query interface targeting 
    the persisted local BGE ChromaDB vector database collection.
    """
    def __init__(self, db_dir: str = "rag/vector_db"):
        self.db_dir = db_dir
        # The retrieval embedder configuration MUST match the builder configuration exactly
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cpu'}
        )
        self.vector_db = Chroma(
            persist_directory=self.db_dir, 
            embedding_function=self.embeddings
        )

    def retrieve_clinical_context(self, user_query: str, top_k: int = 3) -> List[str]:
        """Queries the local BGE database for semantic matching nodes."""
        # Maximal Marginal Relevance (MMR) balances relevance with structural diversity
        retrieved_nodes = self.vector_db.max_marginal_relevance_search(
            query=user_query, 
            k=top_k,
            fetch_k=10
        )
        
        compiled_contexts = []
        for doc in retrieved_nodes:
            page_num = doc.metadata.get("page", "Unknown Page")
            clean_text = doc.page_content.replace("\n", " ").strip()
            compiled_contexts.append(f"[ICMR Manual - Page {page_num}]: {clean_text}")
            
        return compiled_contexts
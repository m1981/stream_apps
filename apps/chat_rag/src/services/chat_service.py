from typing import List, Dict, Tuple
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import HumanMessage, AIMessage
from src.domain.interfaces import VectorStore
from langchain.docstore.document import Document

class ChatService:
    def __init__(self,
                 vector_store: VectorStore,
                 model_name: str = "gpt-4",
                 temperature: float = 1.0):
        self.vector_store = vector_store
        self.chat_model = ChatOpenAI(
            model_name=model_name,
            temperature=temperature
        )
        self.chain = self._create_chain()
        self.chat_history = []

    def _create_chain(self) -> ConversationalRetrievalChain:
        return ConversationalRetrievalChain.from_llm(
            self.chat_model,
            retriever=self.vector_store.as_retriever(
                search_kwargs={"k": 4}
            ),
            return_source_documents=True,
            verbose=True,
        )

    def process_query(self, query: str) -> Tuple[str, List[Dict]]:
        response = self.chain({
            "question": query,
            "chat_history": self.chat_history
        })

        answer = response["answer"]
        sources = response["source_documents"]

        self._update_chat_history(query, answer)

        return answer, self._format_sources(sources)

    def _update_chat_history(self, query: str, answer: str) -> None:
        self.chat_history.append(HumanMessage(content=query))
        self.chat_history.append(AIMessage(content=answer))

    def _format_sources(self, sources: List[Document]) -> List[Dict]:
        return [{
            'folder': doc.metadata['folder'],
            'title': doc.metadata['title'],
            'message_number': doc.metadata['message_number'],
            'content': doc.page_content[:160]
        } for doc in sources]
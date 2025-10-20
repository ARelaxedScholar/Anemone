import asyncio
from os import wait
from uuid import uuid4
import chromadb 

class ChromaMemory:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, client_type, **kwargs):
        if not hasattr(self, "_initialized"):
            self.client = self._client_maker(client_type, **kwargs)
            self._initialized = True

    def save_memory(self, memory, collection="agent_memory"):
        collection = self.client.get_or_create_collection(collection)
        collection.upsert(documents=[memory], ids=[str(uuid4())])

    def retrieve_memory(self, query, collection="agent_memory"):
        collection = self.client.get_or_create_collection(collection)
        retrieved = collection.query(query_texts=[query], n_results=1)["documents"]
        print(retrieved)
        return query, retrieved

    def _client_maker(self, client_type = "persistent", **kwargs):
        match client_type:
            case "persistent":
                try:
                    memory_path = kwargs["memory_path"]
                except KeyError:
                    raise ValueError(f"You have called _client_maker without specifying 'memory_path'")
                return chromadb.PersistentClient(path=memory_path)
            case "ephemeral":
                 return chromadb.EphemeralClient()
            case "http":
                try:
                    host = kwargs["host"]
                except KeyError:
                    raise ValueError("You have called _client_maker without specifying 'host'")
                try:
                    port = kwargs["port"]
                except KeyError:
                    raise ValueError("You have called _client_maker without specifying 'port'")
                return chromadb.HttpClient(host=host, port=int(port))
            case _:
                raise ValueError("Silly goose, you didn't pass a supported 'client_type'")

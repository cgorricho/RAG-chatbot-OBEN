### OBEN GROUP - PROYECTO DE INTELIGENCIA ARTIFICIAL ###
#
# Archivo base para webapp prototipo
# Chatbot con documentos
#
# Desarrollado por:
# Carlos Gorricho
# cel: +57 314 771 0660
# email: carlosgorricho@hobengroup.co

### IMPORTAR DEPENDENCIAS ###
import streamlit as st
from PyPDF2 import PdfReader
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain import hub
from langchain.schema.runnable import RunnablePassthrough, RunnableParallel
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import PromptTemplate
from typing import List
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
# from langchain_pinecone import PineconeVectorStore
from pydantic import BaseModel, Field
import dotenv
import os
import re

### DEFINICION DE LA PAGINA ###

# Configuración de la página
st.set_page_config(
    page_title = 'OBEN GROUP - Chatbot',
    # page_icon = '🏭',
    layout = 'wide'
)

# carga variables de entorno de .env
dotenv.load_dotenv()

### DEFINICION DE FUNCIONES

# define funciones iniciales de procesamiento de texto

# extrae texto de PDF
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# extrae text chunks (pedazos de texto)
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2048, 
        chunk_overlap=256)
    chunks = text_splitter.create_documents([text])
    return chunks

# vector store chromadb
def get_vector_store(text_chunks):
    Chroma.from_documents(documents=text_chunks,
                          embedding=OpenAIEmbeddings(model='text-embedding-3-large'), 
                          persist_directory="./chroma_db",
                          )
    
# crea la barra lateral
with st.sidebar:
        st.image("Logo Oben Group_gris.png")
        # st.title("Pasos:")
        # pdf_docs = st.file_uploader('Cargue el manual de interés y haga click en "Enviar & Procesar"', 
        #                             accept_multiple_files=True, 
        #                             key="pdf_uploader")
        # if st.button("Enviar & Procesar", 
        #              key="process_button"):
        #     with st.spinner("Procesando..."):
        #         raw_text = get_pdf_text(pdf_docs)
        #         st.write(f'Largo del texto: {len(raw_text)}')
        #         text_chunks = get_text_chunks(raw_text)
        #         st.write(f'Número de bloques: {len(text_chunks)}')
        #         get_vector_store(text_chunks)
        #         st.success("Documento procesado")

        st.title('Modelo LLM:')
        
        modelo = st.radio(
            "Seleccione el modelo",
            ["gpt-3.5", "gpt-4", "gpt-4o", "gpt-4o-mini"],
            index=2)
        
        if modelo == "gpt-3.5":
            llm = 'gpt-3.5-turbo-0125'
        elif modelo == "gpt-4":
            llm = 'gpt-4-turbo'
        elif modelo == 'gpt-4o':
            llm = 'gpt-4o'
        else:
            llm = 'gpt-4o-mini'



# Crea layout para el encabezado en la página principal
col1, col2 = st.columns([1, 5])

with col1:
   st.image("Logo Oben Group_gris.png")

with col2:
   st.header('Chatbot con manuales de operación')

with st.expander("Instrucciones"):

    st.markdown("""

    Este chatbot esta diseñado para interactuar con los manuales de operación y mantenimiento de la planta BOPET (Brückner) de Oben Group en Colombia
                
    ### Cómo funciona:

    Siga los siguientes pasos para interactuar con el chatbot:

    1. **Manuales**: El sistema tiene cargado en la base de datos los siguientes manuales:
    * VOLUME 00 - OverviewDocumentation
    * VOLUME 01 - OperatingManual-LineOverview
    * VOLUME 02 - LineOperationManual
    * VOLUME 03 - OperatingManual
    * VOLUME 04 - OperatingManual-Oven
    * VOLUME 05 - OperatingManual-WinderUnit
    * VOLUME 06 - OperatingManual-VacuumSystem
    * VOLUME 07 - OperatingManual-InlineCoatingDevice
    * VOLUME 08 - OperatingManual-FilmRecycling
    * VOLUME 09 - OperatingManual-AuxiliaryWinder
    * VOLUME 10 - OperatingManual-DiePreheatingStation
    * VOLUME 11 - OperatingManual-PullRollUnit

    2. **Seleccione el Modelo (BARRA LATERAL)**: La app utiliza por defecto el mdoelo GPT 4o. El usuasio puede escoger otros modelos para probar el desempeño de la app y la calidad de las respuestas.
                
    3. **Haga sus preguntas (PAGINA PRINCIPAL)**: Después de procesar los documentos, haga cualquier pregunta relacionada con el contenido de los documentos que ha subido.
    
    """)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_source(context, n=10):
    all_pages = []

    for doc in context:
        print('**'*25)
        page = ((re.findall('(VOLUME\s+\d+\s+-\s+[A-Za-z\-]*\s+-\s+Pag\s+\d+\s+)', doc.page_content))) 
        print(page)
        all_pages.extend(page)

    source_pages = '  - ' + '\n\n  - '.join([pg for pg in list(sorted(set(all_pages)))[:n]])
    
    return source_pages


def get_conversational_chain(retriever, llm=llm):
    template = """Use the following pieces of context to answer the question at the end. Always answer the question in the language in which it is asked. If you don't know the answer, just say that you don't know, don't try to make up an answer. Give your responses primarily in numbered lists. 
    
    If the question is related to many documents in the context, try to include the reference for the main titles in your response.
    
    Example:
    "user question: procedure for starting the oven?"

    "helpful answer: The procedure is detailed in various documents. Here is a summary of the main steps:
    1. Main step (Volume 1 - Page 351)
        - Step 1
        - Step 2
    2. Secondary step (Volume 10 - Pag 1322)
        - Step 1
        - Step 2"
    
    {context}

    Question: {question}

    Helpful Answer:
    """

    rag_prompt_custom = PromptTemplate.from_template(template)
    
    llm = ChatOpenAI(model=llm, 
                     temperature=0,
                     )
    
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | rag_prompt_custom
        | llm
        | StrOutputParser()
        )

    rag_chain_with_source = RunnableParallel(
        {"context": retriever, 
         "question": RunnablePassthrough()}
        ).assign(answer=rag_chain_from_docs)
    
    return rag_chain_with_source


def user_input(user_question, llm=llm):
    
    embeddings = OpenAIEmbeddings(model='text-embedding-3-large')
    
    new_db = Chroma(persist_directory="./chroma_db",
                    embedding_function=embeddings,
                    )
    
    multi_retriever = MultiQueryRetriever.from_llm(
        retriever = new_db.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 5, 'fetch_k': 25},
            ), 
        llm = ChatOpenAI(
            model=llm, 
            temperature=0,
            ),
    )    
    
    chain = get_conversational_chain(multi_retriever)
    
    response=chain.invoke(user_question)
    
    return response


def main():
    st.header("Chatbot de IA")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Realice una pregunta acerca de los manuales", key="user_question")
    
    if prompt:
        # agrega la siguiente pregunta al stack de mensajes
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt})

        # despliega pregunta del usuario en la ventana de chat
        with st.chat_message("user"):
            st.markdown(prompt)

        

        with st.chat_message("assistant"):
            
            response = user_input(prompt)
            
            response_with_source = f"""
                {response['answer']}
                \n\nFuente (Source):
                \n\n{get_source(response['context'])}
                """    

            st.markdown(response_with_source)
        
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_with_source})



if __name__ == "__main__":
    main()

#!/bin/bash
curl -fsSL https://ollama.com/install.sh | sh

ollama pull llama3.2

export OLLAMA_HOST=127.0.0.1 # environment variable to set ollama host
export OLLAMA_PORT=11434 # environment variable to set the ollama port


pip install -U ollama langchain_ollama
ollama serve # start the ollama server
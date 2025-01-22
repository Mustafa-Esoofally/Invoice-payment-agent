from setuptools import setup, find_packages

setup(
    name="invoice-payment-agent",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "langchain-openai",
        "composio-langchain"
    ]
) 
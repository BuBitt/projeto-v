import requests
from xml.etree import ElementTree as ET
import polars as pl
from datetime import datetime


def fetch_articles(term, email, years=5, max_results=100):
    base_url_search = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    # Definindo o ano limite
    current_year = datetime.now().year
    start_year = current_year - years
    date_range = f"{start_year}/01/01:{current_year}/12/31"

    search_params = {
        "db": "pubmed",
        "term": f"{term} AND ({date_range}[Date - Publication])",
        "retmax": 1,  # Só precisamos do número total de resultados
        "usehistory": "y",
        "email": email,
    }

    # Fazendo a busca inicial para obter o número total de artigos
    search_response = requests.get(base_url_search, params=search_params)
    search_response.raise_for_status()
    search_results = search_response.text

    # Analisando o XML para obter WebEnv, QueryKey e o número total de resultados
    search_root = ET.fromstring(search_results)
    webenv = search_root.find("WebEnv").text
    query_key = search_root.find("QueryKey").text
    total_results = int(search_root.find("Count").text)

    print(f"Total articles found: {total_results}")

    # Dividindo em lotes para buscar todos os artigos
    all_articles = []
    for start in range(0, total_results, max_results):
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        fetch_params = {
            "db": "pubmed",
            "query_key": query_key,
            "WebEnv": webenv,
            "retstart": start,
            "retmax": max_results,
            "retmode": "xml",
            "email": email,
        }

        fetch_response = requests.get(fetch_url, params=fetch_params)
        fetch_response.raise_for_status()
        fetch_results = fetch_response.text

        # Analisando o XML dos detalhes dos artigos
        fetch_root = ET.fromstring(fetch_results)
        articles = fetch_root.findall(".//DocSum")

        for article in articles:
            title = article.find("Item[@Name='Title']").text
            authors = [
                author.text
                for author in article.findall("Item[@Name='AuthorList']/Item")
            ]
            pub_date = article.find("Item[@Name='PubDate']").text
            doi = (
                article.find("Item[@Name='ELocationID']").text
                if article.find("Item[@Name='ELocationID']") is not None
                else "N/A"
            )
            citation = f"{', '.join(authors)} ({pub_date}). {title}. DOI: {doi}"

            all_articles.append(
                {
                    "Title": title,
                    "Authors": ", ".join(authors),
                    "Publication Date": pub_date,
                    "DOI": doi,
                    "Citation": citation,
                }
            )

        # Exibindo um progresso
        print(f"Fetched {start + len(articles)} de {total_results} artigos")

    # Criando o DataFrame com Polars
    df = pl.DataFrame(all_articles)
    df.write_csv("articles.csv")
    return df


df_articles = fetch_articles("memoria", "algum@estudante.ufcg.edu.br")
print(df_articles)

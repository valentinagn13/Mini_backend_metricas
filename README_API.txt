DATA QUALITY ASSESSMENT API - DOCUMENTATION
============================================

OVERVIEW
--------
This Python backend API implements 17 data quality criteria calculations for dataset assessment.
All calculations follow the exact formulas specified in the requirements.

INSTALLATION
------------
1. Install dependencies:
   pip install -r requirements.txt

2. Download Spanish language model for spaCy (optional, for advanced NLP):
   python -m spacy download es_core_news_sm

RUNNING THE SERVER
------------------
Start the server on http://localhost:8000:
   python main.py

Or using uvicorn directly:
   uvicorn main:app --host 0.0.0.0 --port 8000

API ENDPOINTS
-------------

1. POST /initialize
   Initialize the dataset before calculating criteria.

   Request Body:
   {
     "dataset_url": "https://api.example.com/data.json",
     "metadata": {
       "titulo": "Dataset Title",
       "descripcion": "Dataset description",
       "fecha_actualizacion": "2025-11-01",
       "frecuencia_actualizacion_dias": 30,
       "fuente": "Data source",
       "publicador": "Publisher name",
       "licencia": "License type",
       "tags": ["tag1", "tag2"],
       "attribution_links": ["https://example.com"],
       "etiqueta_fila": "Row label description",
       "columnas": {
         "column_name": {"descripcion": "Column description"}
       }
     }
   }

2. GET /confidencialidad
   Calculates confidentiality score (0-10)
   Evaluates protection of personal and sensitive data

3. GET /relevancia
   Calculates relevance score (0-10)
   Evaluates if data provides value for decision-making

4. GET /actualidad
   Calculates timeliness score (0-10)
   Evaluates data currency based on update frequency

5. GET /trazabilidad
   Calculates traceability score (0-10)
   Evaluates metadata completeness and audit trail

6. GET /conformidad
   Calculates conformity score (0-10)
   Evaluates adherence to standards and conventions

7. GET /exactitudSintactica
   Calculates syntactic accuracy score (0-10)
   Evaluates structural correctness of data

8. GET /exactitudSemantica
   Calculates semantic accuracy score (0-10)
   Evaluates contextual correctness of data

9. GET /completitud
   Calculates completeness score (0-10)
   Evaluates proportion of required values present

10. GET /consistencia
    Calculates consistency score (0-10)
    Evaluates data coherence and lack of contradictions

11. GET /precision
    Calculates precision score (0-10)
    Evaluates appropriate level of data disaggregation

12. GET /portabilidad
    Calculates portability score (0-10)
    Evaluates ease of data transfer across systems

13. GET /credibilidad
    Calculates credibility score (0-10)
    Evaluates trustworthiness based on metadata

14. GET /comprensibilidad
    Calculates comprehensibility score (0-10)
    Evaluates quality of descriptions and labels

15. GET /accesibilidad
    Calculates accessibility score (0-10)
    Evaluates ease of finding and accessing data

16. GET /unicidad
    Calculates uniqueness score (0-10)
    Evaluates absence of duplicates

17. GET /eficiencia
    Calculates efficiency score (0-10)
    Evaluates resource requirements for processing

18. GET /recuperabilidad
    Calculates recoverability score (0-10)
    Evaluates ease of data recovery and understanding

19. GET /disponibilidad
    Calculates availability score (0-10)
    Evaluates data availability and currency

20. GET /all_scores
    Returns all 17 criteria scores in a single response

RESPONSE FORMAT
---------------
Individual endpoints return:
{
  "score": 7.45
}

/all_scores endpoint returns:
{
  "confidencialidad": 8.50,
  "relevancia": 9.00,
  ...
}

TESTING
-------
Run the test example:
   python test_example.py

IMPLEMENTATION DETAILS
----------------------
- All formulas implement exact specifications including exponential and quadratic penalties
- Scores are normalized to 0-10 scale
- Missing metadata receives default scores (typically mid-range)
- Text similarity uses TF-IDF vectorization with cosine similarity
- Special characters detection uses regex patterns
- Sensitive column detection uses pattern matching

METADATA REQUIREMENTS
---------------------
For optimal results, provide complete metadata including:
- titulo: Dataset title
- descripcion: Detailed description
- fecha_actualizacion: Last update date (ISO format)
- frecuencia_actualizacion_dias: Update frequency in days
- fuente: Data source
- publicador: Publisher name
- licencia: License information
- tags: List of search tags
- attribution_links: List of attribution URLs
- etiqueta_fila: Row label description
- columnas: Dictionary with column descriptions

NOTES
-----
- The API processes JSON datasets from URL endpoints (GET request)
- All calculations are performed in-memory
- Scores are cached per calculator instance
- Server must be reinitialized for each new dataset assessment

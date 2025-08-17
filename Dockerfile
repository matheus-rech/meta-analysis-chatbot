# Meta-Analysis Chatbot Docker Image
FROM python:3.11

# Install R and required system dependencies
# Using apt-get to install R base and common packages for better reliability
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-cran-jsonlite \
    r-cran-ggplot2 \
    r-cran-knitr \
    r-cran-rmarkdown \
    r-cran-readxl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install remaining R packages that aren't available via apt
# Using http mirror for better connectivity and graceful failure handling
RUN Rscript -e " \
    options(repos = c(CRAN = 'http://cran.rstudio.com/')); \
    packages <- c('meta', 'metafor', 'base64enc', 'evaluate'); \
    for(pkg in packages) { \
        tryCatch({ \
            if(!require(pkg, character.only=TRUE, quietly=TRUE)) { \
                install.packages(pkg, quiet=TRUE); \
                cat('Installed:', pkg, '\n'); \
            } else { \
                cat('Already available:', pkg, '\n'); \
            } \
        }, error = function(e) { \
            cat('Warning: Failed to install', pkg, ':', e$message, '\n'); \
        }); \
    }" || echo "Warning: Some R packages may not have installed due to network issues"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-chatbot.txt

# Run the main application
CMD ["python", "chatbot_langchain.py"]
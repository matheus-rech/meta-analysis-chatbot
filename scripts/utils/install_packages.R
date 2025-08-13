#!/usr/bin/env Rscript

# Install required R packages for meta-analysis MVP

cat("Installing required R packages for Meta-Analysis MCP Server...\n\n")

# List of required packages
required_packages <- c(
  "jsonlite",   # For JSON handling
  "metafor",    # For meta-analysis calculations
  "ggplot2",     # For advanced visualizations
  "base64enc"  # For encoding plots
)

# Function to install packages if not already installed
install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    cat(paste("Installing", pkg, "...\n"))
    install.packages(pkg, repos = "https://cran.r-project.org")
  } else {
    cat(paste(pkg, "is already installed\n"))
  }
}

# Install each package
for (pkg in required_packages) {
  tryCatch({
    install_if_missing(pkg)
  }, error = function(e) {
    cat(paste("Error installing", pkg, ":", e$message, "\n"))
  })
}

# Verify installation
cat("\nVerifying installations...\n")
all_installed <- TRUE

for (pkg in required_packages) {
  if (requireNamespace(pkg, quietly = TRUE)) {
    cat(paste("✓", pkg, "version", packageVersion(pkg), "\n"))
  } else {
    cat(paste("✗", pkg, "not installed\n"))
    all_installed <- FALSE
  }
}

if (all_installed) {
  cat("\nAll required packages installed successfully!\n")
} else {
  cat("\nSome packages failed to install. Please check the errors above.\n")
  quit(status = 1)
}
#!/usr/bin/env Rscript

# Test script for validating the functionality of R scripts
# Run this with: Rscript test_scripts.R

# Load necessary libraries
library(jsonlite)
library(meta)
library(metafor)

# Get script directory for relative paths
script_dir <- dirname(commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))][1])
script_dir <- gsub("--file=", "", script_dir)

# Source the scripts to test
source(file.path(script_dir, "mcp_server.R"))

# Create test directory
test_dir <- file.path(script_dir, "..", "test_results")
dir.create(test_dir, showWarnings = FALSE, recursive = TRUE)

# Helper function to run tests
run_test <- function(name, test_fn) {
  cat("Running test:", name, "... ")
  result <- tryCatch({
    test_fn()
    cat("PASSED\n")
    TRUE
  }, error = function(e) {
    cat("FAILED\n")
    cat("  Error:", e$message, "\n")
    FALSE
  })
  return(result)
}

# Test 1: Test script loading
test_script_loading <- function() {
  # If we got here, scripts loaded successfully
  stopifnot(exists("main"))
}

# Test 2: Test JSON parsing
test_json_parsing <- function() {
  test_json <- '{"key1": "value1", "key2": 42, "key3": [1, 2, 3]}'
  parsed <- fromJSON(test_json)
  stopifnot(parsed$key1 == "value1")
  stopifnot(parsed$key2 == 42)
  stopifnot(length(parsed$key3) == 3)
}

# Test 3: Create a mock dataset for testing
create_test_dataset <- function() {
  # Create a simple test dataset for meta-analysis
  data <- data.frame(
    study = c("Study 1", "Study 2", "Study 3", "Study 4", "Study 5"),
    n1 = c(100, 150, 200, 120, 180),
    event1 = c(40, 70, 100, 50, 90),
    n2 = c(100, 150, 200, 120, 180),
    event2 = c(30, 50, 80, 40, 70)
  )
  
  # Save to test directory
  write.csv(data, file.path(test_dir, "test_data.csv"), row.names = FALSE)
  return(file.path(test_dir, "test_data.csv"))
}

# Run the tests
test_results <- c(
  run_test("Script loading", test_script_loading),
  run_test("JSON parsing", test_json_parsing)
)

# Summary
cat("\nTest Summary:\n")
cat("  Passed:", sum(test_results), "/", length(test_results), "\n")
cat("  Failed:", sum(!test_results), "/", length(test_results), "\n")

if (sum(!test_results) > 0) {
  quit(status = 1)
}
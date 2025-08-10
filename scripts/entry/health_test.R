#!/usr/bin/env Rscript

# Health test script for checking R environment and dependencies
# This script provides a simple health check endpoint for monitoring

# Check R environment
check_r_environment <- function() {
  r_version <- R.version.string
  return(list(
    version = r_version,
    status = "ok"
  ))
}

# Check required packages
check_packages <- function() {
  required_packages <- c(
    "jsonlite", 
    "meta", 
    "metafor", 
    "ggplot2", 
    "forestplot", 
    "knitr", 
    "rmarkdown", 
    "dplyr", 
    "readxl"
  )
  
  results <- list()
  
  for (pkg in required_packages) {
    if (pkg %in% rownames(installed.packages())) {
      version <- as.character(packageVersion(pkg))
      results[[pkg]] <- list(
        status = "ok",
        version = version
      )
    } else {
      results[[pkg]] <- list(
        status = "error",
        message = paste("Package", pkg, "is not installed")
      )
    }
  }
  
  # Overall packages status
  all_ok <- all(sapply(results, function(x) x$status == "ok"))
  
  return(list(
    status = ifelse(all_ok, "ok", "error"),
    packages = results
  ))
}

# Check system resources
check_system_resources <- function() {
  mem_info <- gc()
  return(list(
    status = "ok",
    memory = list(
      used_mb = sum(mem_info[,2]) / 1024,
      available = TRUE
    ),
    disk = list(
      status = "ok"
    )
  ))
}

# Main health check function
perform_health_check <- function(args) {
  # Default to basic check if not specified
  check_type <- if (!is.null(args$check_type)) args$check_type else "basic"
  
  # Basic check just returns success without details
  if (check_type == "basic") {
    return(list(
      status = "success",
      message = "R environment is operational"
    ))
  }
  
  # Comprehensive check includes all checks
  if (check_type == "comprehensive") {
    r_env <- check_r_environment()
    packages <- check_packages()
    resources <- check_system_resources()
    
    # Determine overall status
    overall_status <- "success"
    if (packages$status == "error" || resources$status == "error") {
      overall_status <- "error"
    }
    
    return(list(
      status = overall_status,
      r_environment = r_env,
      packages = packages,
      resources = resources,
      timestamp = Sys.time()
    ))
  }
  
  # Unknown check type
  return(list(
    status = "error",
    message = paste("Unknown check type:", check_type)
  ))
}

# Execute if run as a script
if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) > 0) {
    # Parse JSON arguments if provided
    if (length(args) > 1) {
      library(jsonlite)
      check_args <- fromJSON(args[2])
    } else {
      check_args <- list(check_type = "basic")
    }
    
    # Perform health check
    result <- perform_health_check(check_args)
    
    # Output as JSON
    cat(toJSON(result, auto_unbox = TRUE))
  } else {
    cat(toJSON(list(
      status = "error",
      message = "No arguments provided"
    ), auto_unbox = TRUE))
  }
}
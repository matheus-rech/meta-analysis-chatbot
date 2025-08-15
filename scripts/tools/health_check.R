#!/usr/bin/env Rscript

# Health check tool - simple and robust health verification
# This should not fail even if packages are missing

health_check <- function(args) {
  tryCatch({
    check_type <- if (!is.null(args$check_type)) args$check_type else "basic"
    detailed <- if (!is.null(args$detailed)) args$detailed else FALSE
    
    # Basic health check
    if (check_type == "basic" && !detailed) {
      return(list(
        status = "success",
        message = "R backend is operational",
        timestamp = as.character(Sys.time()),
        r_version = R.version.string
      ))
    }
    
    # Detailed health check
    result <- list(
      status = "success",
      timestamp = as.character(Sys.time()),
      r_environment = list(
        version = R.version.string,
        platform = R.version$platform,
        working_dir = getwd()
      )
    )
    
    # Check required packages without loading them
    required_packages <- c("jsonlite", "meta", "metafor", "ggplot2", "knitr", "rmarkdown", "readxl", "base64enc", "evaluate")
    package_status <- list()
    all_packages_ok <- TRUE
    
    for (pkg in required_packages) {
      if (pkg %in% rownames(installed.packages())) {
        tryCatch({
          version <- as.character(packageVersion(pkg))
          package_status[[pkg]] <- list(
            status = "ok",
            version = version
          )
        }, error = function(e) {
          package_status[[pkg]] <- list(
            status = "error",
            message = paste("Error getting version for", pkg)
          )
          all_packages_ok <<- FALSE
        })
      } else {
        package_status[[pkg]] <- list(
          status = "missing",
          message = paste("Package", pkg, "is not installed")
        )
        all_packages_ok <- FALSE
      }
    }
    
    result$packages <- package_status
    
    # Set overall status based on package availability
    if (!all_packages_ok) {
      result$status <- "warning"
      result$message <- "Some required packages are missing, but R backend is functional"
    }
    
    # Check system resources
    mem_info <- gc()
    result$resources <- list(
      memory_mb = round(sum(mem_info[,2]) / 1024, 2),
      temp_dir = tempdir(),
      working_dir = getwd()
    )
    
    return(result)
    
  }, error = function(e) {
    return(list(
      status = "error",
      message = paste("Health check failed:", e$message),
      timestamp = as.character(Sys.time())
    ))
  })
}
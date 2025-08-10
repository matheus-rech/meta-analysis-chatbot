# get_session_status.R
# Get comprehensive status of a meta-analysis session

library(jsonlite)

get_session_status <- function(args) {
  session_path <- args$session_path
  
  # Check if session exists
  if (!dir.exists(session_path)) {
    return(list(
      status = "error",
      message = paste("Session not found:", basename(session_path))
    ))
  }
  
  # Load session configuration
  session_config_path <- file.path(session_path, "session.json")
  if (!file.exists(session_config_path)) {
    return(list(
      status = "error",
      message = "Session configuration not found"
    ))
  }
  
  session_config <- fromJSON(session_config_path)
  
  # Initialize status response
  status_response <- list(
    status = "success",
    session_id = basename(session_path),
    project_name = session_config$name,
    created_at = session_config$createdAt,
    configuration = list(
      study_type = session_config$studyType,
      effect_measure = session_config$effectMeasure,
      analysis_model = session_config$analysisModel
    )
  )
  
  # Check workflow stage
  workflow_stage <- "initialized"
  completed_steps <- c()
  
  # Check for uploaded data
  data_files <- list.files(file.path(session_path, "data"), full.names = TRUE)
  if (length(data_files) > 0) {
    workflow_stage <- "data_uploaded"
    completed_steps <- c(completed_steps, "data_upload")
    
    # Get data info
    if (file.exists(file.path(session_path, "data", "uploaded_data.csv"))) {
      data <- read.csv(file.path(session_path, "data", "uploaded_data.csv"))
      status_response$data_info <- list(
        n_studies = nrow(data),
        columns = names(data)
      )
    }
  }
  
  # Check for analysis results
  results_dir <- file.path(session_path, "results")
  if (file.exists(file.path(results_dir, "analysis_results.rds")) || 
      file.exists(file.path(results_dir, "meta_analysis_results.json"))) {
    workflow_stage <- "analysis_completed"
    completed_steps <- c(completed_steps, "meta_analysis")
  }
  
  # Check for plots
  if (file.exists(file.path(results_dir, "forest_plot.png"))) {
    completed_steps <- c(completed_steps, "forest_plot")
  }
  
  if (file.exists(file.path(results_dir, "funnel_plot.png"))) {
    completed_steps <- c(completed_steps, "funnel_plot")
  }
  
  # Check for bias assessment
  if (file.exists(file.path(results_dir, "publication_bias_results.json"))) {
    completed_steps <- c(completed_steps, "publication_bias")
  }
  
  # Check for report
  report_files <- list.files(results_dir, pattern = "meta_analysis_report\\.(html|pdf|docx)", full.names = TRUE)
  if (length(report_files) > 0) {
    workflow_stage <- "report_generated"
    completed_steps <- c(completed_steps, "report")
  }
  
  # Set workflow stage
  status_response$workflow_stage <- workflow_stage
  status_response$completed_steps <- completed_steps
  
  # List all generated files
  files <- list()
  
  # Data files
  if (length(data_files) > 0) {
    files$data <- basename(data_files)
  }
  
  # Result files
  if (dir.exists(results_dir)) {
    result_files <- list.files(results_dir, full.names = FALSE)
    if (length(result_files) > 0) {
      files$results <- result_files
    }
  }
  
  # Processing files
  processing_dir <- file.path(session_path, "processing")
  if (dir.exists(processing_dir)) {
    processing_files <- list.files(processing_dir, full.names = FALSE)
    if (length(processing_files) > 0) {
      files$processing <- processing_files
    }
  }
  
  status_response$files <- files
  
  # Add next steps recommendations
  next_steps <- c()
  
  if (workflow_stage == "initialized") {
    next_steps <- c("Upload study data using 'upload_study_data' tool")
  } else if (workflow_stage == "data_uploaded") {
    next_steps <- c("Perform meta-analysis using 'perform_meta_analysis' tool")
  } else if (workflow_stage == "analysis_completed") {
    if (!"forest_plot" %in% completed_steps) {
      next_steps <- c(next_steps, "Generate forest plot using 'generate_forest_plot' tool")
    }
    if (!"publication_bias" %in% completed_steps) {
      next_steps <- c(next_steps, "Assess publication bias using 'assess_publication_bias' tool")
    }
    if (!"report" %in% completed_steps) {
      next_steps <- c(next_steps, "Generate comprehensive report using 'generate_report' tool")
    }
  }
  
  if (length(next_steps) > 0) {
    status_response$next_steps <- next_steps
  }
  
  return(status_response)
}
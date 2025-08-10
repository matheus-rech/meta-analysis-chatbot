# direct_upload_data.R
# Alternative upload function that accepts direct CSV file paths
# Useful for testing and direct R usage

library(jsonlite)

upload_study_data_direct <- function(args) {
  session_path <- args$session_path
  csv_file_path <- args$csv_file_path  # Direct file path instead of base64
  
  # Validate file exists
  if (!file.exists(csv_file_path)) {
    stop(paste("CSV file not found:", csv_file_path))
  }
  
  # Create data directory if it doesn't exist
  data_dir <- file.path(session_path, "data")
  if (!dir.exists(data_dir)) {
    dir.create(data_dir, recursive = TRUE)
  }
  
  # Read and validate CSV
  tryCatch({
    data <- read.csv(csv_file_path, stringsAsFactors = FALSE)
    
    # Basic validation
    if (nrow(data) < 2) {
      stop("Dataset must contain at least 2 studies")
    }
    
    # Check for required columns based on data type
    binary_cols <- c("study_id", "events_treatment", "n_treatment", "events_control", "n_control")
    continuous_cols <- c("study_id", "mean_treatment", "sd_treatment", "n_treatment", 
                        "mean_control", "sd_control", "n_control")
    generic_cols <- c("study_id", "effect_size", "se")
    
    has_binary <- all(binary_cols %in% colnames(data))
    has_continuous <- all(continuous_cols %in% colnames(data))
    has_generic <- all(generic_cols %in% colnames(data))
    
    if (!has_binary && !has_continuous && !has_generic) {
      stop("Data must contain columns for binary outcomes, continuous outcomes, or generic effect sizes")
    }
    
    # Determine data type
    data_type <- if(has_binary) "binary" else if(has_continuous) "continuous" else "generic"
    
    # Save the data
    saveRDS(data, file.path(data_dir, "uploaded_data.rds"))
    write.csv(data, file.path(data_dir, "uploaded_data.csv"), row.names = FALSE)
    
    # Return validation summary
    list(
      status = "success",
      message = "Data uploaded and validated successfully",
      data_type = data_type,
      n_studies = nrow(data),
      columns = names(data),
      validation_summary = list(
        has_missing = any(is.na(data)),
        study_ids_unique = length(unique(data$study_id)) == nrow(data)
      )
    )
    
  }, error = function(e) {
    list(
      status = "error",
      message = paste("Error processing CSV file:", e$message)
    )
  })
}
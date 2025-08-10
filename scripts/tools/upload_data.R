# upload_data.R

library(jsonlite)
library(readxl)
library(metafor)

# Maximum file size in bytes (50MB)
MAX_FILE_SIZE <- 50 * 1024 * 1024

upload_study_data <- function(args) {
  session_path <- args$session_path
  
  # Decode base64 data content
  data_content <- args$data_content
  
  # Check input size before processing
  if (!is.null(args$data_content)) {
    content_size <- nchar(args$data_content, type = "bytes")
    
    # For base64, actual decoded size is roughly 3/4 of encoded size
    if (grepl("^[A-Za-z0-9+/=]+$", args$data_content) && nchar(args$data_content) %% 4 == 0) {
      estimated_decoded_size <- ceiling(content_size * 0.75)
      if (estimated_decoded_size > MAX_FILE_SIZE) {
        stop(sprintf("File size exceeds maximum allowed size of %d MB", MAX_FILE_SIZE / (1024 * 1024)))
      }
    } else if (content_size > MAX_FILE_SIZE) {
      stop(sprintf("File size exceeds maximum allowed size of %d MB", MAX_FILE_SIZE / (1024 * 1024)))
    }
  } else {
    stop("No data content provided")
  }
  
  # Create input directory if it doesn't exist
  input_dir <- file.path(session_path, "input")
  if (!dir.exists(input_dir)) {
    dir.create(input_dir, recursive = TRUE)
  }
  
  # Write data to file
  raw_data_path <- file.path(input_dir, paste0("raw_data.", args$data_format))
  
  # Handle base64 encoded data
  if (grepl("^[A-Za-z0-9+/=]+$", args$data_content) && nchar(args$data_content) %% 4 == 0) {
    decoded_data <- base64enc::base64decode(args$data_content)
    
    # Double-check decoded size
    if (length(decoded_data) > MAX_FILE_SIZE) {
      stop(sprintf("Decoded file size exceeds maximum allowed size of %d MB", MAX_FILE_SIZE / (1024 * 1024)))
    }
    
    writeBin(decoded_data, raw_data_path)
  } else {
    writeLines(args$data_content, raw_data_path)
  }
  
  # Check file size after writing
  file_info <- file.info(raw_data_path)
  if (!is.na(file_info$size) && file_info$size > MAX_FILE_SIZE) {
    # Clean up the file
    unlink(raw_data_path)
    stop(sprintf("Written file size exceeds maximum allowed size of %d MB", MAX_FILE_SIZE / (1024 * 1024)))
  }
  
  # Load data based on format with memory protection
  tryCatch({
    # Pre-check for CSV to avoid loading huge files into memory
    if (args$data_format == "csv") {
      # Quick check: count lines without loading full file
      line_count <- length(readLines(raw_data_path, n = 10001))
      if (line_count > 10000) {
        stop("CSV file has too many rows (maximum 10,000 allowed)")
      }
    }
    
    loaded_data <- switch(args$data_format,
      "csv" = read.csv(raw_data_path, stringsAsFactors = FALSE, nrows = 10000),
      "excel" = {
        # For Excel, we can't easily pre-check row count
        data <- read_excel(raw_data_path)
        if (nrow(data) > 10000) {
          stop("Excel file has too many rows (maximum 10,000 allowed)")
        }
        data
      },
      "revman" = stop("RevMan format not yet implemented"),
      stop("Unsupported data format: ", args$data_format)
    )
    
    # Additional safety check on loaded data
    if (nrow(loaded_data) > 10000) {
      stop("Data has too many rows (maximum 10,000 allowed)")
    }
    
    # Check memory usage (rough estimate)
    data_size <- object.size(loaded_data)
    if (data_size > MAX_FILE_SIZE) {
      stop(sprintf("Loaded data size exceeds maximum allowed size of %d MB", MAX_FILE_SIZE / (1024 * 1024)))
    }
    
  }, error = function(e) {
    # Clean up on error
    if (file.exists(raw_data_path)) {
      unlink(raw_data_path)
    }
    stop("Failed to load data: ", e$message)
  })
  
  # Get outcome type from session config
  session_config_path <- file.path(session_path, "session.json")
  if (!file.exists(session_config_path)) {
    stop("Session configuration not found")
  }
  session_config <- fromJSON(session_config_path)
  # Normalize field names from camelCase to snake_case for internal use
  if (is.null(session_config$effect_measure) && !is.null(session_config$effectMeasure)) {
    session_config$effect_measure <- session_config$effectMeasure
  }
  if (is.null(session_config$analysis_model) && !is.null(session_config$analysisModel)) {
    session_config$analysis_model <- session_config$analysisModel
  }
  if (is.null(session_config$study_type) && !is.null(session_config$studyType)) {
    session_config$study_type <- session_config$studyType
  }
  
  # Canonicalize and map common column schemas to expected names
  names(loaded_data) <- tolower(names(loaded_data))
  # Map study identifiers if needed, with warnings and type validation
  if (!"study" %in% names(loaded_data)) {
    if ("study_id" %in% names(loaded_data)) {
      loaded_data$study <- loaded_data$study_id
      # No warning for primary mapping
    } else if ("studlab" %in% names(loaded_data)) {
      loaded_data$study <- loaded_data$studlab
      warning("Mapped 'studlab' to 'study' as study identifier. Please check data consistency.")
    } else if ("id" %in% names(loaded_data)) {
      loaded_data$study <- loaded_data$id
      warning("Mapped 'id' to 'study' as study identifier. Please check data consistency.")
    } else if ("author" %in% names(loaded_data)) {
      loaded_data$study <- loaded_data$author
      warning("Mapped 'author' to 'study' as study identifier. Please check data consistency.")
    }
    # Validate type of mapped study column
    if ("study" %in% names(loaded_data) && !(is.character(loaded_data$study) || is.factor(loaded_data$study))) {
      warning("Mapped 'study' column is not character or factor. Please check data types.")
    }
  }
  if (is.null(session_config$effect_measure)) {
    stop("Session configuration missing required field: effect_measure")
  }
  em <- toupper(session_config$effect_measure)
  # Binary outcomes (OR/RR): map treatment/control schemas
  if (em %in% c("OR","RR")) {
    if (all(c("events_treatment","n_treatment","events_control","n_control") %in% names(loaded_data))) {
      loaded_data$event1 <- loaded_data$events_treatment
      loaded_data$n1    <- loaded_data$n_treatment
      loaded_data$event2 <- loaded_data$events_control
      loaded_data$n2    <- loaded_data$n_control
    } else if (all(c("event.e","n.e","event.c","n.c") %in% names(loaded_data))) {
      loaded_data$event1 <- loaded_data[["event.e"]]
      loaded_data$n1     <- loaded_data[["n.e"]]
      loaded_data$event2 <- loaded_data[["event.c"]]
      loaded_data$n2     <- loaded_data[["n.c"]]
      warning("Mapped RevMan-style columns (event.e/n.e/event.c/n.c) to event1/n1/event2/n2. Please verify.")
    }
  }
  # Continuous outcomes (MD/SMD)
  if (em %in% c("MD","SMD")) {
    if (all(c("mean_treatment","sd_treatment","n_treatment","mean_control","sd_control","n_control") %in% names(loaded_data))) {
      loaded_data$mean1 <- loaded_data$mean_treatment
      loaded_data$sd1   <- loaded_data$sd_treatment
      loaded_data$n1    <- loaded_data$n_treatment
      loaded_data$mean2 <- loaded_data$mean_control
      loaded_data$sd2   <- loaded_data$sd_control
      loaded_data$n2    <- loaded_data$n_control
    } else if (all(c("mean.e","sd.e","n.e","mean.c","sd.c","n.c") %in% names(loaded_data))) {
      loaded_data$mean1 <- loaded_data[["mean.e"]]
      loaded_data$sd1   <- loaded_data[["sd.e"]]
      loaded_data$n1    <- loaded_data[["n.e"]]
      loaded_data$mean2 <- loaded_data[["mean.c"]]
      loaded_data$sd2   <- loaded_data[["sd.c"]]
      loaded_data$n2    <- loaded_data[["n.c"]]
      warning("Mapped RevMan-style columns (mean.e/sd.e/n.e/mean.c/sd.c/n.c) to mean1/sd1/n1/mean2/sd2/n2. Please verify.")
    }
  }
  # Single-arm proportion: map events/n
  if (em == "PROP") {
    if (!"events" %in% names(loaded_data)) {
      for (candidate in c("event", "positives", "cases", "successes", "x")) {
        if (candidate %in% names(loaded_data)) {
          loaded_data$events <- loaded_data[[candidate]]
          break
        }
      }
    }
    if (!"n" %in% names(loaded_data)) {
      for (candidate in c("total", "sample_size", "n_total", "nobs", "size", "n")) {
        if (candidate %in% names(loaded_data)) {
          loaded_data$n <- loaded_data[[candidate]]
          break
        }
      }
    }
  }
  
  # Validate data structure based on effect measure
  validation_result <- validate_data_structure(loaded_data, session_config$effect_measure)
  if (!validation_result$valid) {
    stop("Data validation failed: ", validation_result$message)
  }
  
  # Process data for meta-analysis
  processed_data <- process_study_data(loaded_data, session_config)
  
  # Create processing directory if it doesn't exist
  processing_dir <- file.path(session_path, "processing")
  if (!dir.exists(processing_dir)) {
    dir.create(processing_dir, recursive = TRUE)
  }
  
  # Save the processed data
  processed_data_path <- file.path(processing_dir, "processed_data.rds")
  saveRDS(processed_data, file = processed_data_path)
  
  list(
    status = "success",
    message = paste("Data uploaded and validated successfully"),
    validation_results = list(
      issues = list(),
      studies_count = nrow(processed_data)
    )
  )
}

# Validate data structure
validate_data_structure <- function(data, effect_measure) {
  required_cols <- switch(effect_measure,
    "OR" = c("study", "event1", "n1", "event2", "n2"),
    "RR" = c("study", "event1", "n1", "event2", "n2"),
    "MD" = c("study", "mean1", "sd1", "n1", "mean2", "sd2", "n2"),
    "SMD" = c("study", "mean1", "sd1", "n1", "mean2", "sd2", "n2"),
    "HR" = c("study", "hr", "se_hr"),
    "PROP" = c("study", "events", "n"),
    "MEAN" = c("study", "n", "mean", "sd"),
    stop("Unsupported effect measure: ", effect_measure)
  )
  
  # Check if all required columns exist (case-insensitive)
  data_cols <- tolower(names(data))
  missing_cols <- setdiff(tolower(required_cols), data_cols)
  
  if (length(missing_cols) > 0) {
    return(list(
      valid = FALSE,
      message = paste("Missing required columns:", paste(missing_cols, collapse = ", "))
    ))
  }
  
  # Check for valid data types and values
  if (nrow(data) == 0) {
    return(list(valid = FALSE, message = "No data rows found"))
  }
  
  # Additional validation checks could go here
  
  return(list(valid = TRUE, message = "Data structure is valid"))
}

# Process study data for meta-analysis
process_study_data <- function(data, session_config) {
  effect_measure <- session_config$effect_measure
  
  # Standardize column names to lowercase
  names(data) <- tolower(names(data))
  
  # Calculate effect sizes using escalc
  processed_data <- switch(effect_measure,
    "OR" = escalc(measure = "OR", 
                  ai = data$event1, n1i = data$n1, 
                  ci = data$event2, n2i = data$n2,
                  data = data),
    "RR" = escalc(measure = "RR", 
                  ai = data$event1, n1i = data$n1, 
                  ci = data$event2, n2i = data$n2,
                  data = data),
    "MD" = escalc(measure = "MD", 
                  m1i = data$mean1, sd1i = data$sd1, n1i = data$n1,
                  m2i = data$mean2, sd2i = data$sd2, n2i = data$n2,
                  data = data),
    "SMD" = escalc(measure = "SMD", 
                   m1i = data$mean1, sd1i = data$sd1, n1i = data$n1,
                   m2i = data$mean2, sd2i = data$sd2, n2i = data$n2,
                   data = data),
    "HR" = {
      # For hazard ratios, we expect log HR and SE
      data$yi <- log(data$hr)
      data$vi <- data$se_hr^2
      data
    },
    "PROP" = {
      # Normalize event(s)/n column names
      if (!"events" %in% names(data) && "event" %in% names(data)) data$events <- data$event
      data$yi <- data$events / data$n
      data$vi <- (data$yi * (1 - data$yi)) / pmax(data$n, 1)
      data
    },
    "MEAN" = {
      # Single-arm continuous: keep as-is; adapter will use metamean
      data
    },
    stop("Unsupported effect measure: ", effect_measure)
  )
  
  # Add study labels if not present
  if (!"study" %in% names(processed_data)) {
    processed_data$study <- paste("Study", seq_len(nrow(processed_data)))
  }
  
  return(processed_data)
}
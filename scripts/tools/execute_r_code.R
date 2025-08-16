# scripts/tools/execute_r_code.R

# Ensure required packages are available (best-effort installs when missing)
if (!requireNamespace("base64enc", quietly = TRUE)) {
  try({ install.packages("base64enc", repos = "https://cloud.r-project.org") }, silent = TRUE)
}
if (!requireNamespace("evaluate", quietly = TRUE)) {
  try({ install.packages("evaluate", repos = "https://cloud.r-project.org") }, silent = TRUE)
}

execute_r_code <- function(args) {
  # Accept either args$code (preferred) or args$r_code (back-compat)
  code_to_execute <- args$code
  if (is.null(code_to_execute) && !is.null(args$r_code)) {
    code_to_execute <- args$r_code
  }
  session_path <- args$session_path

  if (is.null(code_to_execute) || !is.character(code_to_execute) || length(code_to_execute) != 1) {
    return(list(status = "error", message = "No 'code' argument provided or it is not a single string."))
  }

  if (is.null(session_path)) {
    session_path <- getwd()
  }

  # Ensure the tmp directory exists
  tmp_dir <- file.path(session_path, "tmp")
  dir.create(tmp_dir, showWarnings = FALSE, recursive = TRUE)
  plot_path <- tempfile(pattern = "r_plot_", tmpdir = tmp_dir, fileext = ".png")

  # Use a clean environment for execution
  exec_env <- new.env(parent = .GlobalEnv)

  # Variables to store outputs
  output_text <- ""
  warnings_text <- c()
  errors_text <- c()
  plot_data <- NULL

  # Graphics handler: save the most recent plot to plot_path
  save_plot_safely <- function(plot_obj) {
    tryCatch({
      grDevices::png(plot_path, width = 8, height = 6, units = "in", res = 150)
      print(plot_obj)
      grDevices::dev.off()
    }, error = function(e) {
      # swallow graphics errors into warnings
      warnings_text <<- c(warnings_text, paste("Graphics error:", conditionMessage(e)))
      try({ grDevices::dev.off() }, silent = TRUE)
    })
  }

  # Custom output handler for the evaluate function
  oh <- evaluate::new_output_handler(
    text = function(o) {
      output_text <<- paste0(output_text, o)
    },
    graphics = function(p) {
      # p is a recorded plot or expression that can be printed
      save_plot_safely(p)
    },
    message = function(m) {
      # Treat messages as regular output
      output_text <<- paste0(output_text, conditionMessage(m))
    },
    warning = function(w) {
      warnings_text <<- c(warnings_text, conditionMessage(w))
    },
    error = function(e) {
      errors_text <<- c(errors_text, conditionMessage(e))
    }
  )

  # Execute the code
  tryCatch({
    evaluate::evaluate(code_to_execute, envir = exec_env, output_handler = oh)
  }, error = function(e) {
    errors_text <<- c(errors_text, conditionMessage(e))
  })

  # Check if a plot was created and encode it
  if (file.exists(plot_path) && file.info(plot_path)$size > 0) {
    plot_data <- base64enc::base64encode(plot_path)
  }

  # Clean up the temp plot file (best-effort)
  if (file.exists(plot_path)) {
    try({ unlink(plot_path) }, silent = TRUE)
  }

  # Prepare the response
  response <- list(
    status   = if (length(errors_text) > 0) "error" else "success",
    stdout   = if (nzchar(trimws(output_text))) trimws(output_text) else NULL,
    warnings = if (length(warnings_text) > 0) warnings_text else NULL,
    error    = if (length(errors_text) > 0) paste(errors_text, collapse = "\n") else NULL,
    plot     = plot_data
  )

  return(response)
}

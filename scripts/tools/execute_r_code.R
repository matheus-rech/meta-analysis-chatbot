# scripts/tools/execute_r_code.R

# Ensure required packages are available
if (!requireNamespace("base64enc", quietly = TRUE)) {
  install.packages("base64enc", repos = "https://cloud.r-project.org")
}
if (!requireNamespace("evaluate", quietly = TRUE)) {
  install.packages("evaluate", repos = "https://cloud.r-project.org")
}

execute_r_code <- function(args) {
  code_to_execute <- args$code
  session_path <- args$session_path

  if (is.null(code_to_execute) || !is.character(code_to_execute) || length(code_to_execute) != 1) {
    return(list(status = "error", message = "No 'code' argument provided or it is not a single string."))
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

  # Custom output handler for the evaluate function
  output_handler <- evaluate::new_output_handler(
    text = function(o) {
      output_text <<- paste(output_text, o, sep = "")
    },
    graphics = function(p) {
      # A plot was generated, save it
      tryCatch({
        png(plot_path, width = 8, height = 6, units = "in", res = 300)
        print(p)
      }, finally = {
        if (grDevices::dev.cur() != 1) {
      dev_prev <- grDevices::dev.cur()
      tryCatch({
        png(plot_path, width = 8, height = 6, units = "in", res = 300)
        dev_png <- grDevices::dev.cur()
        print(p)
      }, finally = {
        # Close the PNG device if it is still open
        if (exists("dev_png") && grDevices::dev.cur() == dev_png) {
          grDevices::dev.off(dev_png)
        }
      })
    },
    message = function(m) {
      # Treat messages as regular output
      output_text <<- paste(output_text, conditionMessage(m), sep = "")
    },
    warning = function(w) {
      warnings_text <<- c(warnings_text, conditionMessage(w))
    },
    error = function(e) {
      # Capture error message and stop execution
      errors_text <<- c(errors_text, conditionMessage(e))
    }
  )

  # Use evaluate to run the code
  evaluate::evaluate(code_to_execute, envir = exec_env, output_handler = output_handler)

  # Check if a plot was created and encode it
  if (file.exists(plot_path) && file.info(plot_path)$size > 0) {
    plot_data <- base64enc::base64encode(plot_path)
  }

  # Clean up the temp plot file
  if (file.exists(plot_path)) {
    unlink(plot_path)
  }

  # Prepare the response
  response <- list(
    status = if (length(errors_text) > 0) "error" else "success",
    stdout = trimws(output_text),
    warnings = if(length(warnings_text) > 0) warnings_text else NULL,
    error = if (length(errors_text) > 0) paste(errors_text, collapse = "\n") else NULL,
    plot = plot_data
  )

  return(response)
}

# scripts/tools/execute_r_code.R

# Safely execute arbitrary R code and capture results, output, and plots.
execute_r_code <- function(args) {
  required_args <- c("r_code")
  if (!all(required_args %in% names(args))) {
    return(list(status = "error", message = "Missing required argument: r_code"))
  }

  r_code <- args$r_code
  session_path <- args$session_path

  # Create a temporary file for the plot
  plot_path <- tempfile(tmpdir = file.path(session_path, "results"), fileext = ".png")

  stdout_capture <- c()
  warnings_capture <- c()
  error_capture <- NULL
  result_val <- NULL

  # Use a custom environment to avoid polluting the global one
  exec_env <- new.env(parent = .GlobalEnv)

  # Open a PNG device to capture any plots
  png(filename = plot_path, width = 8, height = 6, units = "in", res = 300)

  # Use tryCatch to handle everything
  execution_result <- tryCatch({
    # Capture stdout and warnings
    stdout_capture <- capture.output({
      result_val <- withCallingHandlers(
        eval(parse(text = r_code), envir = exec_env),
        warning = function(w) {
          warnings_capture <<- c(warnings_capture, conditionMessage(w))
          invokeRestart("muffleWarning")
        }
      )
    })

    list(status = "success")
  }, error = function(e) {
    error_capture <<- conditionMessage(e)
    list(status = "error")
  })

  # Always close the graphics device
  dev.off()

  # Check if a plot was actually created (file size > 0)
  plot_b64 <- NULL
  if (file.exists(plot_path) && file.info(plot_path)$size > 0) {
    plot_b64 <- base64enc::base64encode(plot_path)
  }
  # Clean up the temp plot file
  if(file.exists(plot_path)) file.remove(plot_path)

  # Serialize the result to a string representation
  result_str <- tryCatch({
    # Use dput to get a reproducible representation of the R object
    paste(capture.output(dput(result_val)), collapse = "\n")
  }, error = function(e) {
    "Result could not be serialized."
  })

  # Construct the final response
  response <- list(
    status = if (is.null(error_capture)) "success" else "error",
    stdout = paste(stdout_capture, collapse = "\n"),
    warnings = paste(warnings_capture, collapse = "\n"),
    error = error_capture,
    returned_result = result_str,
    plot = plot_b64
  )

  return(response)
}

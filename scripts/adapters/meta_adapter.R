# meta_adapter.R
# Adapter layer to integrate meta package functions with MCP server

# Set library path (from meta_analysis.R)
.libPaths(c("~/R/library", .libPaths()))

# Load required libraries
suppressMessages({
  library(meta)
  library(metafor)
  library(jsonlite)
  library(ggplot2)
})

# Core meta-analysis function using meta package
perform_meta_analysis_core <- function(data, method = "random", measure = "OR") {
  
  # Normalize common column names
  if ("study" %in% colnames(data) && !"study_id" %in% colnames(data)) {
    data$study_id <- data$study
  }
  
  # Perform meta-analysis using meta package
  if (measure == "OR" && all(c("events_treatment", "n_treatment", "events_control", "n_control") %in% colnames(data))) {
    # Binary outcome meta-analysis
    meta_method <- if(method == "random") "Inverse" else "MH"
    meta_result <- metabin(
      event.e = data$events_treatment,
      n.e = data$n_treatment,
      event.c = data$events_control,
      n.c = data$n_control,
      studlab = data$study_id,
      method = meta_method,
      sm = "OR",
      random = (method == "random"),
      fixed = (method == "fixed")
    )
  } else if (measure %in% c("MD", "SMD") && (
             all(c("mean_treatment", "sd_treatment", "n_treatment", "mean_control", "sd_control", "n_control") %in% colnames(data)) ||
             all(c("n.e", "mean.e", "sd.e", "n.c", "mean.c", "sd.c") %in% colnames(data))
           )) {
    # Continuous outcome meta-analysis (supports both treatment/control and e/c schemas)
    if (all(c("n.e", "mean.e", "sd.e", "n.c", "mean.c", "sd.c") %in% colnames(data))) {
      n_e <- data$n.e; mean_e <- data$mean.e; sd_e <- data$sd.e
      n_c <- data$n.c; mean_c <- data$mean.c; sd_c <- data$sd.c
    } else {
      n_e <- data$n_treatment; mean_e <- data$mean_treatment; sd_e <- data$sd_treatment
      n_c <- data$n_control; mean_c <- data$mean_control; sd_c <- data$sd_control
    }
    meta_result <- metacont(
      n.e = n_e,
      mean.e = mean_e,
      sd.e = sd_e,
      n.c = n_c,
      mean.c = mean_c,
      sd.c = sd_c,
      studlab = data$study_id,
      sm = measure,
      random = (method == "random"),
      fixed = (method == "fixed")
    )
  } else if (measure == "PROP" && (all(c("events", "n") %in% colnames(data)) || all(c("event", "n") %in% colnames(data)))) {
    # Single-arm proportion meta-analysis
    # Canonicalize column names
    if ("event" %in% colnames(data) && !"events" %in% colnames(data)) {
      data$events <- data$event
    }
    # Determine transformation automatically per guidance
    pvec <- if (all(c("events","n") %in% colnames(data))) data$events / pmax(data$n, 1) else {
      if ("yi" %in% colnames(data)) data$yi else rep(NA_real_, nrow(data))
    }
    pvec <- suppressWarnings(as.numeric(pvec))
    pvec <- pvec[is.finite(pvec)]
    prop_sm <- "PRAW"
    if (length(pvec) > 0) {
      has_extremes <- any(pvec <= 0 | pvec >= 1)
      mean_p <- mean(pvec, na.rm = TRUE)
      if (has_extremes) prop_sm <- "PFT" else if (mean_p < 0.2 || mean_p > 0.8) prop_sm <- "PLOGIT" else prop_sm <- "PRAW"
    }
    # Prefer GLMM for single-arm meta-analysis per recommendations
    meta_result <- metaprop(
      event = data$events,
      n = data$n,
      studlab = if("study_id" %in% colnames(data)) data$study_id else NULL,
      method = "GLMM",
      sm = prop_sm,
      random = (method == "random"),
      fixed = (method == "fixed")
    )
  } else if (measure == "MEAN" && all(c("n", "mean", "sd") %in% colnames(data))) {
    # Single-arm continuous meta-analysis (metamean)
    meta_result <- metamean(
      n = data$n,
      mean = data$mean,
      sd = data$sd,
      studlab = if("study_id" %in% colnames(data)) data$study_id else NULL,
      sm = "MRAW",
      random = (method == "random"),
      fixed = (method == "fixed")
    )
  } else if ("effect_size" %in% colnames(data) && "se" %in% colnames(data)) {
    # Generic inverse variance meta-analysis
    meta_result <- metagen(
      TE = if(measure == "OR") log(data$effect_size) else data$effect_size,
      seTE = data$se,
      studlab = data$study_id,
      sm = measure,
      random = (method == "random"),
      fixed = (method == "fixed")
    )
  } else {
    stop("Required columns not found for the specified effect measure")
  }
  
  return(meta_result)
}

# Function to convert metafor data format to meta package format
convert_metafor_to_meta_format <- function(data, session_config) {
  # If data already has the right columns, return as is
  required_binary <- c("events_treatment", "n_treatment", "events_control", "n_control")
  required_continuous <- c("mean_treatment", "sd_treatment", "n_treatment", "mean_control", "sd_control", "n_control")
  required_prop <- c("events", "n")
  
  if (all(required_binary %in% colnames(data)) || all(required_continuous %in% colnames(data)) || all(required_prop %in% colnames(data))) {
    return(data)
  }
  
  # If data has yi and vi (metafor format), we need additional info from session
  if (all(c("yi", "vi") %in% colnames(data))) {
    # For now, create a generic format
    # In a real implementation, we'd need to store the original data format
    converted <- data.frame(
      study_id = if("study" %in% colnames(data)) data$study else paste("Study", seq_len(nrow(data))),
      effect_size = if(!is.null(session_config$effectMeasure) && session_config$effectMeasure == "OR") exp(data$yi) else data$yi,
      se = sqrt(data$vi)
    )
    return(converted)
  }
  
  return(data)
}

# Generate forest plot using meta package
generate_forest_plot_core <- function(meta_result, output_file, title = "Forest Plot", 
                                    plot_style = "classic", confidence_level = 0.95,
                                    custom_labels = NULL) {
  
  # Set plot dimensions based on number of studies
  n_studies <- length(meta_result$TE)
  plot_height <- max(600, 100 + n_studies * 40)
  
  # Generate forest plot
  png(output_file, width = 1200, height = plot_height, res = 150)
  
  # Customize based on plot style
  if (plot_style == "modern") {
    # Modern style with colors
    forest(meta_result,
           main = title,
           xlab = paste("Effect Size (", meta_result$sm, ")", sep = ""),
           xlim = "symmetric",
           col.diamond = "#2E86AB",
           col.diamond.lines = "#2E86AB",
           col.square = "#A23B72",
           col.square.lines = "#A23B72",
           col.inside = "white",
           fontsize = 12,
           spacing = 1.3,
           squaresize = 0.5,
           lwd = 2,
           print.I2 = TRUE,
           print.tau2 = TRUE,
           print.pval.Q = TRUE,
           leftcols = c("studlab", "event.e", "n.e", "event.c", "n.c"),
           leftlabs = if(!is.null(custom_labels$left)) custom_labels$left else NULL,
           rightcols = c("effect", "ci", "w.random"),
           rightlabs = if(!is.null(custom_labels$right)) custom_labels$right else c("Effect", "95% CI", "Weight"))
  } else if (plot_style == "journal_specific") {
    # Journal style - more compact
    forest(meta_result,
           main = title,
           xlab = paste("Effect Size (", meta_result$sm, ")", sep = ""),
           col.diamond = "black",
           col.diamond.lines = "black",
           col.square = "black",
           col.square.lines = "black",
           fontsize = 10,
           spacing = 1.0,
           squaresize = 0.4)
  } else {
    # Classic style (default) - using styling from original meta_analysis.R
    forest(meta_result,
           main = title,
           xlab = paste("Effect Size (", meta_result$sm, ")", sep = ""),
           comb.fixed = FALSE,
           comb.random = TRUE,
           overall = TRUE,
           hetstat = TRUE,
           print.tau2 = TRUE,
           print.I2 = TRUE,
           col.diamond = "blue",
           col.diamond.lines = "black",
           col.square = "red",
           col.square.lines = "black",
           col.inside = "white",
           fontsize = 12,
           spacing = 1.2)
  }
  
  dev.off()
  
  return(output_file)
}

# Generate funnel plot using meta package
generate_funnel_plot_core <- function(meta_result, output_file, title = "Funnel Plot") {
  
  # Generate funnel plot
  png(output_file, width = 800, height = 600, res = 150)
  
  # Create funnel plot - enhanced with original styling
  funnel(meta_result,
         main = title,
         xlab = paste("Effect Size (", meta_result$sm, ")", sep = ""),
         ylab = "Standard Error",
         col = "blue",
         bg = "blue",
         pch = 16,
         cex = 1.2,
         contour = c(0.9, 0.95, 0.99),
         col.contour = c("darkgray", "gray", "lightgray"),
         lwd = 2)
  
  dev.off()
  
  return(output_file)
}

# Assess publication bias using meta package
assess_publication_bias_core <- function(meta_result) {
  
  results <- list()
  
  # Egger's test
  egger_test <- metabias(meta_result, method.bias = "linreg", plotit = FALSE)
  results$egger_test <- list(
    statistic = egger_test$statistic,
    p_value = egger_test$p.value,
    interpretation = ifelse(egger_test$p.value < 0.05,
                          "Significant evidence of publication bias",
                          "No significant evidence of publication bias")
  )
  
  # Begg's test
  begg_test <- metabias(meta_result, method.bias = "rank", plotit = FALSE)
  results$begg_test <- list(
    statistic = begg_test$statistic,
    p_value = begg_test$p.value,
    interpretation = ifelse(begg_test$p.value < 0.05,
                          "Significant evidence of publication bias",
                          "No significant evidence of publication bias")
  )
  
  # Trim and fill analysis if requested
  if (meta_result$k >= 5) {  # Only if enough studies
    tf <- try(trimfill(meta_result), silent = TRUE)
    if (!inherits(tf, "try-error")) {
      results$trim_fill <- list(
        studies_added = tf$k0,
        adjusted_estimate = if(!is.null(tf$TE.random)) tf$TE.random else tf$TE.fixed,
        interpretation = paste("Trim-and-fill added", tf$k0, "studies")
      )
    }
  }
  
  return(results)
}
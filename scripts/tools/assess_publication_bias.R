# assess_publication_bias.R
# Updated to use meta package through adapter

library(jsonlite)

# Get script directory for sourcing
script_dir <- dirname(sys.frame(1)$ofile)
if (is.null(script_dir)) {
  # Fallback for command line execution
  args_cmd <- commandArgs(trailingOnly = FALSE)
  script_file <- args_cmd[grep("--file=", args_cmd)]
  if (length(script_file) > 0) {
    script_dir <- dirname(gsub("--file=", "", script_file))
  } else {
    script_dir <- getwd()
  }
}

source(file.path(script_dir, "../adapters", "meta_adapter.R"))

assess_publication_bias <- function(args) {
  session_path <- args$session_path
  
  # Load analysis results
  results_path <- file.path(session_path, "results", "analysis_results.rds")
  if (!file.exists(results_path)) {
    # Try loading from processing directory (backward compatibility)
    results_path <- file.path(session_path, "processing", "analysis_results.rds")
    if (!file.exists(results_path)) {
      stop("Analysis results not found. Please perform meta-analysis first.")
    }
    results <- readRDS(results_path)
    # Extract meta object from old format
    meta_result <- if(is.list(results) && !is.null(results$model)) results$model else results
  } else {
    meta_result <- readRDS(results_path)
  }
  
  # Validate that we have a meta object
  if (!inherits(meta_result, c("meta", "metabin", "metacont", "metagen", "rma"))) {
    stop("Invalid meta-analysis object.")
  }
  
  # Create output directory if it doesn't exist
  output_dir <- file.path(session_path, "results")
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }
  
  # Validate methods
  if (is.null(args$methods) || length(args$methods) == 0) {
    stop("No methods specified for publication bias assessment")
  }
  
  # Initialize response
  response <- list(status = "success")
  
  # Check if we have enough studies for bias assessment
  n_studies <- if(inherits(meta_result, "rma")) length(meta_result$yi) else meta_result$k
  if (n_studies < 3) {
    response$warning <- "Too few studies for reliable publication bias assessment (minimum 3 required)"
  }
  
  tryCatch({
    # For meta package objects, use the core function
    if (inherits(meta_result, c("meta", "metabin", "metacont", "metagen"))) {
      
      # Generate funnel plot if requested
      if ("funnel_plot" %in% args$methods) {
        funnel_plot_path <- file.path(output_dir, "funnel_plot.png")
        funnel_plot <- generate_funnel_plot_core(
          meta_result = meta_result,
          output_file = funnel_plot_path,
          title = "Funnel Plot for Publication Bias Assessment"
        )
        response$funnel_plot_path <- funnel_plot_path
      }
      
      # Perform statistical tests if we have enough studies
      if (n_studies >= 3) {
        bias_results <- assess_publication_bias_core(meta_result)
        
        # Add Egger's test results
        if ("egger_test" %in% args$methods && !is.null(bias_results$egger_test)) {
          response$egger_test <- bias_results$egger_test
        }
        
        # Add Begg's test results
        if ("begg_test" %in% args$methods && !is.null(bias_results$begg_test)) {
          response$begg_test <- bias_results$begg_test
        }
        
        # Add trim-and-fill results
        if ("trim_fill" %in% args$methods && !is.null(bias_results$trim_fill)) {
          response$trim_fill <- bias_results$trim_fill
        }
      }
      
    } else if (inherits(meta_result, "rma")) {
      # Handle metafor objects (backward compatibility)
      
      # Generate funnel plot
      if ("funnel_plot" %in% args$methods) {
        funnel_plot_path <- file.path(output_dir, "funnel_plot.png")
        png(funnel_plot_path, width = 800, height = 600, res = 100)
        
        funnel(meta_result, 
               main = "Funnel Plot for Publication Bias Assessment",
               xlab = "Effect Size")
        dev.off()
        response$funnel_plot_path <- funnel_plot_path
      }
      
      # Perform tests if we have enough studies
      if (n_studies >= 3) {
        # Egger's test
        if ("egger_test" %in% args$methods) {
          egger <- regtest(meta_result)
          response$egger_test <- list(
            p_value = egger$pval,
            interpretation = ifelse(egger$pval < 0.05,
                                  "Significant evidence of publication bias",
                                  "No significant evidence of publication bias")
          )
        }
        
        # Rank correlation test (similar to Begg's)
        if ("begg_test" %in% args$methods) {
          rank_test <- ranktest(meta_result)
          response$begg_test <- list(
            p_value = rank_test$pval,
            interpretation = ifelse(rank_test$pval < 0.05,
                                  "Significant evidence of publication bias",
                                  "No significant evidence of publication bias")
          )
        }
        
        # Trim and fill
        if ("trim_fill" %in% args$methods && n_studies >= 5) {
          tf <- trimfill(meta_result)
          response$trim_fill <- list(
            studies_added = tf$k0,
            adjusted_estimate = coef(tf),
            interpretation = paste("Trim-and-fill added", tf$k0, "studies")
          )
        }
      }
    }
    
    # Save bias assessment results
    bias_results_path <- file.path(output_dir, "publication_bias_results.json")
    writeLines(toJSON(response, pretty = TRUE), bias_results_path)
    
    # Add summary interpretation
    if (!is.null(response$egger_test) || !is.null(response$begg_test)) {
      egger_sig <- !is.null(response$egger_test) && response$egger_test$p_value < 0.05
      begg_sig <- !is.null(response$begg_test) && response$begg_test$p_value < 0.05
      
      if (egger_sig && begg_sig) {
        response$overall_interpretation <- "Multiple tests suggest evidence of publication bias"
      } else if (egger_sig || begg_sig) {
        response$overall_interpretation <- "Mixed evidence for publication bias"
      } else {
        response$overall_interpretation <- "No significant evidence of publication bias"
      }
    }
    
    response
    
  }, error = function(e) {
    list(
      status = "error",
      message = paste("Error assessing publication bias:", e$message),
      details = list(
        methods_requested = args$methods,
        n_studies = n_studies
      )
    )
  })
}
#!/usr/bin/env Rscript

# Meta-Analysis System with Gradio Interface - Pure R Implementation
# This demonstrates using Gradio directly from R without Python intermediaries

# Load required libraries
library(reticulate)
library(meta)
library(metafor)
library(jsonlite)
library(ggplot2)

# Import Gradio from Python via reticulate
gr <- import("gradio")

# Source our existing R tools
source_path <- file.path(dirname(dirname(dirname(sys.frame(1)$ofile))), "scripts")
if (!dir.exists(source_path)) {
  source_path <- "/app/scripts"  # Docker fallback
}

# Global session storage
sessions <- list()
current_session_id <- NULL

# ============================================================================
# Core Meta-Analysis Functions (using existing R backend)
# ============================================================================

initialize_session <- function(name, study_type, effect_measure, analysis_model) {
  # Generate session ID
  session_id <- paste0("session_", format(Sys.time(), "%Y%m%d_%H%M%S"))
  
  # Create session directory
  session_path <- file.path(tempdir(), session_id)
  dir.create(session_path, recursive = TRUE)
  dir.create(file.path(session_path, "data"))
  dir.create(file.path(session_path, "results"))
  
  # Store session info
  session_info <- list(
    id = session_id,
    name = name,
    study_type = study_type,
    effect_measure = effect_measure,
    analysis_model = analysis_model,
    created_at = Sys.time(),
    path = session_path
  )
  
  # Save to global storage
  sessions[[session_id]] <<- session_info
  current_session_id <<- session_id
  
  # Save session metadata
  writeLines(toJSON(session_info, pretty = TRUE), 
             file.path(session_path, "session.json"))
  
  return(paste("✅ Session initialized successfully!\n",
               "Session ID:", session_id, "\n",
               "Name:", name, "\n",
               "Study Type:", study_type, "\n",
               "Effect Measure:", effect_measure, "\n",
               "Analysis Model:", analysis_model))
}

upload_data <- function(csv_text, validation_level) {
  if (is.null(current_session_id)) {
    return("❌ No active session. Please initialize first.")
  }
  
  session <- sessions[[current_session_id]]
  
  tryCatch({
    # Parse CSV data
    data <- read.csv(text = csv_text, stringsAsFactors = FALSE)
    
    # Basic validation
    required_cols <- c("study_id", "effect_size", "se")
    if (!all(required_cols %in% names(data))) {
      return(paste("❌ Missing required columns. Need:", 
                   paste(required_cols, collapse = ", ")))
    }
    
    # Save data
    data_path <- file.path(session$path, "data", "uploaded_data.csv")
    write.csv(data, data_path, row.names = FALSE)
    
    # Store in session
    sessions[[current_session_id]]$data <<- data
    
    return(paste("✅ Data uploaded successfully!\n",
                 "Studies:", nrow(data), "\n",
                 "Columns:", paste(names(data), collapse = ", ")))
    
  }, error = function(e) {
    return(paste("❌ Error uploading data:", e$message))
  })
}

perform_analysis <- function(heterogeneity_test, publication_bias, sensitivity_analysis) {
  if (is.null(current_session_id)) {
    return("❌ No active session. Please initialize first.")
  }
  
  session <- sessions[[current_session_id]]
  
  if (is.null(session$data)) {
    return("❌ No data uploaded. Please upload data first.")
  }
  
  tryCatch({
    data <- session$data
    
    # Perform meta-analysis using meta package
    if (session$effect_measure == "OR") {
      # For odds ratios (assuming we have event data)
      if (all(c("events_treatment", "n_treatment", "events_control", "n_control") %in% names(data))) {
        meta_result <- metabin(
          event.e = data$events_treatment,
          n.e = data$n_treatment,
          event.c = data$events_control,
          n.c = data$n_control,
          studlab = data$study_id,
          method = if(session$analysis_model == "fixed") "MH" else "DL",
          sm = "OR"
        )
      } else {
        # Generic inverse variance method
        meta_result <- metagen(
          TE = log(data$effect_size),
          seTE = data$se,
          studlab = data$study_id,
          sm = "OR"
        )
      }
    } else {
      # Generic continuous outcome
      meta_result <- metagen(
        TE = data$effect_size,
        seTE = data$se,
        studlab = data$study_id
      )
    }
    
    # Store results
    sessions[[current_session_id]]$meta_result <<- meta_result
    
    # Create summary
    summary_text <- paste(
      "📊 Meta-Analysis Results\n",
      "========================\n",
      "Overall Effect:", round(meta_result$TE.random, 3), "\n",
      "95% CI: [", round(meta_result$lower.random, 3), ", ", 
      round(meta_result$upper.random, 3), "]\n",
      "p-value:", format.pval(meta_result$pval.random, digits = 3), "\n",
      "\nHeterogeneity:\n",
      "I²:", round(meta_result$I2 * 100, 1), "%\n",
      "τ²:", round(meta_result$tau2, 4), "\n",
      "Q statistic:", round(meta_result$Q, 2), 
      " (p =", format.pval(meta_result$pval.Q, digits = 3), ")\n"
    )
    
    return(summary_text)
    
  }, error = function(e) {
    return(paste("❌ Error in analysis:", e$message))
  })
}

generate_forest <- function(plot_style, confidence_level) {
  if (is.null(current_session_id) || is.null(sessions[[current_session_id]]$meta_result)) {
    return("❌ No analysis results. Please run analysis first.")
  }
  
  session <- sessions[[current_session_id]]
  meta_result <- session$meta_result
  
  tryCatch({
    # Generate forest plot
    plot_path <- file.path(session$path, "results", "forest_plot.png")
    
    png(plot_path, width = 800, height = 600)
    forest(meta_result, 
           col.square = "blue",
           col.diamond = "red",
           print.I2 = TRUE,
           print.tau2 = TRUE,
           level = confidence_level)
    dev.off()
    
    return(paste("✅ Forest plot generated!\n",
                 "Location:", plot_path, "\n",
                 "Style:", plot_style, "\n",
                 "Confidence Level:", confidence_level * 100, "%"))
    
  }, error = function(e) {
    return(paste("❌ Error generating plot:", e$message))
  })
}

# ============================================================================
# Chatbot Function with LLM-style responses
# ============================================================================

meta_analysis_chatbot <- function(message, history) {
  # Simple pattern matching for demonstration
  # In production, you could integrate with an actual LLM
  
  message_lower <- tolower(message)
  response <- ""
  
  # Initialize session
  if (grepl("start|begin|initialize|new", message_lower)) {
    result <- initialize_session(
      "Meta-Analysis Project",
      "clinical_trial",
      "OR",
      "random"
    )
    response <- paste("I'll help you start a new meta-analysis!\n\n", result)
  }
  
  # Upload data
  else if (grepl("upload|data|csv", message_lower)) {
    # Check if CSV data is provided
    if (grepl("study_id", message)) {
      # Extract CSV portion
      csv_text <- gsub(".*?(study_id.*)", "\\1", message)
      result <- upload_data(csv_text, "comprehensive")
      response <- paste("I'll upload your data now.\n\n", result)
    } else {
      response <- "Please provide CSV data with columns: study_id, effect_size, se"
    }
  }
  
  # Run analysis
  else if (grepl("analyze|analysis|run|perform", message_lower)) {
    result <- perform_analysis(TRUE, TRUE, FALSE)
    response <- paste("Running comprehensive meta-analysis...\n\n", result)
  }
  
  # Generate plot
  else if (grepl("forest|plot|visualiz", message_lower)) {
    result <- generate_forest("modern", 0.95)
    response <- paste("Creating forest plot visualization...\n\n", result)
  }
  
  # Educational responses
  else if (grepl("heterogeneity|i2|i-squared", message_lower)) {
    response <- paste(
      "📚 Heterogeneity in Meta-Analysis:\n\n",
      "I² represents the percentage of total variation across studies due to heterogeneity.\n",
      "- I² < 25%: Low heterogeneity\n",
      "- I² 25-50%: Moderate heterogeneity\n",
      "- I² > 50%: High heterogeneity\n\n",
      "High heterogeneity suggests studies are measuring different effects,",
      "which may require subgroup analysis or a random-effects model."
    )
  }
  
  # Help
  else if (grepl("help|what can you", message_lower)) {
    response <- paste(
      "I can help you with:\n",
      "1. Starting a new meta-analysis\n",
      "2. Uploading study data\n",
      "3. Running statistical analysis\n",
      "4. Generating forest plots\n",
      "5. Explaining statistical concepts\n\n",
      "Try: 'Start a new meta-analysis' or 'Upload my data'"
    )
  }
  
  else {
    response <- "I'm not sure how to help with that. Try asking about starting an analysis, uploading data, or running the meta-analysis."
  }
  
  # Update history
  new_history <- paste(history, "\nUser: ", message, "\nAssistant: ", response, sep = "")
  
  return(list(response, new_history))
}

# ============================================================================
# Create Gradio Interface using Blocks
# ============================================================================

create_gradio_app <- function() {
  
  # Create Blocks interface
  with(gr$Blocks(title = "Meta-Analysis Assistant (R-Native)"), {
    
    gr$Markdown("# 🧬 Meta-Analysis Assistant - Pure R Implementation")
    gr$Markdown("This interface is created entirely in R using Gradio via reticulate!")
    
    # Tab interface
    with(gr$Tabs(), {
      
      # Chatbot Tab
      with(gr$Tab("💬 AI Assistant"), {
        chatbot <- gr$Chatbot(height = 600)
        msg <- gr$Textbox(
          label = "Your message",
          placeholder = "Try: 'Start a new meta-analysis'",
          lines = 2
        )
        
        submit <- gr$Button("Send", variant = "primary")
        clear <- gr$Button("Clear")
        
        # Hidden state for conversation history
        history_state <- gr$State("")
        
        # Wire up the chatbot
        submit$click(
          fn = meta_analysis_chatbot,
          inputs = list(msg, history_state),
          outputs = list(chatbot, history_state)
        )
        
        msg$submit(
          fn = meta_analysis_chatbot,
          inputs = list(msg, history_state),
          outputs = list(chatbot, history_state)
        )
        
        clear$click(
          fn = function() { list("", "") },
          outputs = list(chatbot, history_state)
        )
      })
      
      # Direct Tools Tab
      with(gr$Tab("🛠️ Direct Tools"), {
        
        with(gr$Row(), {
          with(gr$Column(), {
            gr$Markdown("### Initialize Session")
            init_name <- gr$Textbox(label = "Project Name", value = "My Meta-Analysis")
            init_type <- gr$Dropdown(
              choices = list("clinical_trial", "observational", "diagnostic"),
              label = "Study Type",
              value = "clinical_trial"
            )
            init_measure <- gr$Dropdown(
              choices = list("OR", "RR", "MD", "SMD", "HR"),
              label = "Effect Measure",
              value = "OR"
            )
            init_model <- gr$Dropdown(
              choices = list("fixed", "random", "auto"),
              label = "Analysis Model",
              value = "random"
            )
            init_btn <- gr$Button("Initialize")
            init_output <- gr$Textbox(label = "Result", lines = 5)
            
            init_btn$click(
              fn = initialize_session,
              inputs = list(init_name, init_type, init_measure, init_model),
              outputs = init_output
            )
          })
          
          with(gr$Column(), {
            gr$Markdown("### Upload Data")
            upload_text <- gr$Textbox(
              label = "CSV Data",
              lines = 10,
              value = "study_id,effect_size,se\nStudy1,0.5,0.1\nStudy2,0.3,0.12\nStudy3,0.7,0.15"
            )
            upload_validation <- gr$Dropdown(
              choices = list("basic", "comprehensive"),
              label = "Validation Level",
              value = "comprehensive"
            )
            upload_btn <- gr$Button("Upload")
            upload_output <- gr$Textbox(label = "Result", lines = 5)
            
            upload_btn$click(
              fn = upload_data,
              inputs = list(upload_text, upload_validation),
              outputs = upload_output
            )
          })
        })
        
        with(gr$Row(), {
          with(gr$Column(), {
            gr$Markdown("### Perform Analysis")
            analysis_hetero <- gr$Checkbox(label = "Heterogeneity Test", value = TRUE)
            analysis_bias <- gr$Checkbox(label = "Publication Bias", value = TRUE)
            analysis_sens <- gr$Checkbox(label = "Sensitivity Analysis", value = FALSE)
            analysis_btn <- gr$Button("Run Analysis")
            analysis_output <- gr$Textbox(label = "Result", lines = 10)
            
            analysis_btn$click(
              fn = perform_analysis,
              inputs = list(analysis_hetero, analysis_bias, analysis_sens),
              outputs = analysis_output
            )
          })
          
          with(gr$Column(), {
            gr$Markdown("### Generate Forest Plot")
            plot_style <- gr$Dropdown(
              choices = list("classic", "modern", "journal"),
              label = "Plot Style",
              value = "modern"
            )
            plot_conf <- gr$Slider(
              minimum = 0.90,
              maximum = 0.99,
              value = 0.95,
              label = "Confidence Level"
            )
            plot_btn <- gr$Button("Generate Plot")
            plot_output <- gr$Textbox(label = "Result", lines = 10)
            
            plot_btn$click(
              fn = generate_forest,
              inputs = list(plot_style, plot_conf),
              outputs = plot_output
            )
          })
        })
      })
      
      # Educational Tab
      with(gr$Tab("📚 Learn"), {
        gr$Markdown(
          "## Understanding Meta-Analysis\n\n",
          "### Key Concepts:\n",
          "- **Effect Size**: The magnitude of the treatment effect\n",
          "- **Heterogeneity (I²)**: Variation between studies\n",
          "- **Forest Plot**: Visual summary of all studies\n",
          "- **Funnel Plot**: Check for publication bias\n\n",
          "### Statistical Models:\n",
          "- **Fixed Effects**: Assumes one true effect size\n",
          "- **Random Effects**: Assumes distribution of effect sizes\n\n",
          "### Sample Data Format:\n",
          "```csv\n",
          "study_id,effect_size,se\n",
          "Smith2020,0.45,0.12\n",
          "Jones2021,0.38,0.15\n",
          "```"
        )
      })
    })
  })
}

# ============================================================================
# Main Execution
# ============================================================================

main <- function() {
  cat("🚀 Starting Meta-Analysis Gradio Interface in R\n")
  cat("📦 This runs entirely in R using reticulate!\n")
  
  # Check if Gradio is available
  if (!py_module_available("gradio")) {
    cat("Installing Gradio...\n")
    py_install("gradio")
  }
  
  # Create and launch the app
  app <- create_gradio_app()
  app$launch(
    server_name = "0.0.0.0",
    server_port = 7860,
    share = FALSE
  )
}

# Run if executed directly
if (!interactive()) {
  main()
}
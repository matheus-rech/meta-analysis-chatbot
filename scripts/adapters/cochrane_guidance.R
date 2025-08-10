# cochrane_guidance.R
# Helper functions for adding Cochrane-aligned recommendations to meta-analysis results

#' Add Cochrane-aligned recommendations to results
#' 
#' @param results The analysis results
#' @param analysis_type The type of analysis performed
#' @return Enhanced results with Cochrane recommendations
add_cochrane_recommendations <- function(results, analysis_type = "meta_analysis") {
  
  # Default recommendations
  recommendations <- list()
  
  if (analysis_type == "meta_analysis") {
    # Get I-squared value and add appropriate recommendation
    i_squared <- results$heterogeneity$i_squared
    
    if (!is.null(i_squared)) {
      if (i_squared > 75) {
        recommendations$heterogeneity <- list(
          finding = "Considerable heterogeneity detected",
          cochrane_guidance = "Cochrane Handbook (Section 10.10.2) suggests exploring sources of heterogeneity through subgroup analyses or meta-regression when substantial heterogeneity exists.",
          suggested_actions = c(
            "Consider if all studies should be combined",
            "Explore potential clinical and methodological differences",
            "Conduct subgroup analyses if enough studies are available",
            "Verify random-effects model is being used"
          )
        )
      } else if (i_squared > 50) {
        recommendations$heterogeneity <- list(
          finding = "Substantial heterogeneity detected",
          cochrane_guidance = "Per Cochrane guidance, moderate to substantial heterogeneity may warrant exploration of potential causes.",
          suggested_actions = c(
            "Consider subgroup analyses for predefined characteristics",
            "Interpret the pooled estimate with caution"
          )
        )
      } else if (i_squared > 30) {
        recommendations$heterogeneity <- list(
          finding = "Moderate heterogeneity detected",
          cochrane_guidance = "Cochrane Handbook notes that I² values between 30-60% may represent moderate heterogeneity.",
          suggested_actions = c(
            "Consider if there are obvious clinical differences between studies",
            "Random-effects model may be appropriate"
          )
        )
      } else {
        recommendations$heterogeneity <- list(
          finding = "Low heterogeneity detected",
          cochrane_guidance = "Cochrane Handbook notes that I² values below 40% may not be important heterogeneity.",
          suggested_actions = c(
            "Fixed-effect model may be appropriate if studies are methodologically similar",
            "Consider if studies are truly measuring the same effect"
          )
        )
      }
    }
    
    # Add power assessment
    study_count <- ifelse(is.null(results$study_count), 0, results$study_count)
    if (study_count < 10) {
      recommendations$statistical_power <- list(
        finding = sprintf("Limited number of studies (%d)", study_count),
        cochrane_guidance = "Cochrane Handbook notes that meta-analyses with few studies have limited power to detect heterogeneity and publication bias.",
        suggested_actions = c(
          "Interpret statistical tests for heterogeneity cautiously",
          "Consider the clinical diversity of included studies",
          "Note limitations in the interpretation of funnel plots with few studies"
        )
      )
    }
    
    # Add effect size interpretation
    if (!is.null(results$overall_effect) && !is.null(results$p_value)) {
      effect_size <- results$overall_effect
      p_value <- results$p_value
      
      if (p_value < 0.05) {
        recommendations$effect_interpretation <- list(
          finding = "Statistically significant effect detected",
          cochrane_guidance = "Cochrane emphasizes considering clinical significance alongside statistical significance.",
          suggested_actions = c(
            "Consider the magnitude of effect in clinical context",
            "Evaluate the quality of evidence using GRADE approach",
            "Consider absolute risk differences alongside relative measures"
          )
        )
      } else {
        recommendations$effect_interpretation <- list(
          finding = "No statistically significant effect detected",
          cochrane_guidance = "Cochrane Handbook cautions against interpreting non-significant results as 'no effect'.",
          suggested_actions = c(
            "Consider if the meta-analysis had sufficient power",
            "Report confidence intervals to show the range of possible effects",
            "Avoid concluding 'no difference' or 'no effect'"
          )
        )
      }
    }
  }
  
  if (analysis_type == "publication_bias") {
    # Add publication bias recommendations
    p_value <- ifelse(is.null(results$egger_test$p_value), 1, results$egger_test$p_value)
    study_count <- ifelse(is.null(results$study_count), 0, results$study_count)
    
    if (study_count < 10) {
      recommendations$test_limitation <- list(
        finding = "Limited number of studies for bias assessment",
        cochrane_guidance = "Cochrane Handbook (Section 13.3.5.1) cautions against using tests for funnel plot asymmetry when there are fewer than 10 studies.",
        suggested_actions = c(
          "Interpret test results with extreme caution",
          "Consider the test results as exploratory only",
          "Focus on other aspects of study quality and risk of bias"
        )
      )
    } else if (p_value < 0.05) {
      recommendations$significant_bias <- list(
        finding = "Potential publication bias detected",
        cochrane_guidance = "Cochrane recommends considering multiple explanations for funnel plot asymmetry beyond publication bias.",
        suggested_actions = c(
          "Consider other sources of asymmetry (heterogeneity, reporting bias)",
          "Assess the robustness of findings with trim-and-fill method",
          "Search for unpublished studies if possible"
        )
      )
    } else {
      recommendations$non_significant_bias <- list(
        finding = "No significant publication bias detected",
        cochrane_guidance = "Cochrane notes that absence of statistical evidence for funnel plot asymmetry cannot be taken as evidence of absence of bias.",
        suggested_actions = c(
          "Continue to consider risk of publication bias",
          "Evaluate the comprehensiveness of the literature search",
          "Consider if selective outcome reporting may be present"
        )
      )
    }
  }
  
  if (analysis_type == "forest_plot") {
    # Add forest plot interpretation guidance
    recommendations$visualization_guidance <- list(
      finding = "Forest plot visualization created",
      cochrane_guidance = "Cochrane Handbook recommends using forest plots to display effect estimates and confidence intervals for all studies and meta-analyses.",
      interpretation_tips = c(
        "Examine the overlap of confidence intervals to visually assess heterogeneity",
        "Check for studies with notably different results that may warrant sensitivity analyses",
        "Consider the weight of each study (indicated by size of squares)",
        "Note that the diamond represents the pooled effect estimate and its width represents the confidence interval"
      )
    )
  }
  
  # Add recommendations to results
  if (length(recommendations) > 0) {
    results$cochrane_recommendations <- recommendations
  }
  
  return(results)
}

#' Add educational content to analysis results
#' 
#' @param results The analysis results
#' @param topic The topic for educational content
#' @return Enhanced results with educational content
add_educational_content <- function(results, topic) {
  educational_content <- list()
  
  if (topic == "heterogeneity") {
    educational_content$definition <- "Heterogeneity in meta-analysis refers to the variability in the intervention effects being evaluated in the different studies."
    educational_content$interpretation <- list(
      i_squared = list(
        description = "Percentage of variation across studies due to heterogeneity rather than chance",
        thresholds = list(
          "0-40%" = "might not be important",
          "30-60%" = "may represent moderate heterogeneity",
          "50-90%" = "may represent substantial heterogeneity",
          ">75%" = "considerable heterogeneity"
        )
      ),
      tau_squared = "Estimate of the between-study variance in a random-effects meta-analysis",
      q_statistic = "Chi-squared statistic for the test of heterogeneity"
    )
    educational_content$reference <- "Cochrane Handbook Section 10.10.2: Identifying and measuring heterogeneity"
  }
  
  if (topic == "effect_measures") {
    educational_content$definition <- "Effect measures quantify the difference in outcomes between intervention and control groups."
    educational_content$types <- list(
      binary = list(
        OR = "Odds Ratio: the ratio of the odds of an event in the treatment group to the odds in the control group",
        RR = "Risk Ratio: the ratio of the risk of an event in the treatment group to the risk in the control group",
        RD = "Risk Difference: the absolute difference in risk between treatment and control groups"
      ),
      continuous = list(
        MD = "Mean Difference: used when outcomes are measured on the same scale across studies",
        SMD = "Standardized Mean Difference: used when studies measure the same outcome using different scales"
      )
    )
    educational_content$choosing <- "Cochrane recommends choosing effect measures based on consistency across studies, ease of interpretation, and mathematical properties."
    educational_content$reference <- "Cochrane Handbook Section 10.5: Choosing effect measures"
  }
  
  # Add educational content to results if available
  if (length(educational_content) > 0) {
    results$educational_content <- educational_content
  }
  
  return(results)
}
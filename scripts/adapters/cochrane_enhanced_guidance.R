# cochrane_enhanced_guidance.R
# Enhanced Cochrane-aligned decision support system for meta-analysis
# This provides deep knowledge and decision trees for LLMs to make informed choices

#' Main decision tree for meta-analysis workflow
#' @param context Current analysis context
#' @return Decision tree with recommendations
get_meta_analysis_decision_tree <- function(context = list()) {
  decision_tree <- list(
    root = "meta_analysis_planning",
    
    # Step 1: Study Selection Decision Tree
    study_selection = list(
      question = "Are you planning study selection?",
      cochrane_ref = "Handbook Chapter 4: Searching for and selecting studies",
      
      criteria = list(
        inclusion = list(
          population = list(
            guidance = "Define using PICO framework (Population, Intervention, Comparator, Outcome)",
            examples = c(
              "Adults (18+) with diagnosed type 2 diabetes",
              "Children (<18) with acute respiratory infection",
              "Pregnant women in third trimester"
            ),
            common_errors = c(
              "Too broad: 'All patients'",
              "Too narrow: 'Males aged 45-46 from urban areas'"
            )
          ),
          
          intervention = list(
            guidance = "Specify the intervention of interest precisely",
            considerations = c(
              "Dose and duration for medications",
              "Frequency and intensity for behavioral interventions",
              "Technical specifications for devices"
            )
          ),
          
          study_design = list(
            hierarchy = c(
              "1. Systematic reviews of RCTs",
              "2. Individual RCTs",
              "3. Quasi-randomized trials",
              "4. Cohort studies (if RCTs not feasible)",
              "5. Case-control studies",
              "6. Cross-sectional studies"
            ),
            cochrane_note = "Cochrane reviews typically include only RCTs for interventions"
          )
        ),
        
        exclusion = list(
          common_criteria = c(
            "Wrong population",
            "Wrong intervention",
            "Wrong comparator",
            "Wrong outcomes",
            "Wrong study design",
            "Duplicate publication",
            "Insufficient data reported"
          ),
          documentation = "Document reasons for exclusion at full-text review stage"
        )
      ),
      
      decision_rules = list(
        if_few_studies = list(
          condition = "n_studies < 5",
          recommendation = "Consider narrative synthesis instead of meta-analysis",
          rationale = "Statistical synthesis may be unreliable with very few studies"
        ),
        
        if_heterogeneous_designs = list(
          condition = "multiple_study_designs",
          recommendation = "Analyze different designs separately",
          rationale = "Mixing study designs can introduce bias and heterogeneity"
        )
      )
    ),
    
    # Step 2: Effect Measure Selection Decision Tree
    effect_measure_selection = list(
      question = "What type of outcome are you analyzing?",
      cochrane_ref = "Handbook Section 6.4: Choosing effect measures",
      
      binary_outcomes = list(
        definition = "Outcomes with two possible values (yes/no, alive/dead, cured/not cured)",
        
        measures = list(
          odds_ratio = list(
            when_to_use = c(
              "Case-control studies",
              "When baseline risk varies substantially",
              "For mathematical properties in modeling"
            ),
            interpretation = "OR > 1 indicates increased odds with intervention",
            advantages = c(
              "Symmetrical (OR of A vs B = 1/OR of B vs A)",
              "Not affected by outcome prevalence",
              "Can be used in logistic regression"
            ),
            disadvantages = c(
              "Difficult to interpret for non-statisticians",
              "Often misinterpreted as risk ratio",
              "Can exaggerate effects when events are common"
            ),
            cochrane_recommendation = "Use when events are rare (<10%) or for case-control studies"
          ),
          
          risk_ratio = list(
            when_to_use = c(
              "Prospective studies (RCTs, cohort)",
              "When communicating to clinicians",
              "When baseline risks are similar"
            ),
            interpretation = "RR > 1 indicates increased risk with intervention",
            advantages = c(
              "Intuitive interpretation",
              "Direct measure of risk",
              "Preferred by clinicians"
            ),
            disadvantages = c(
              "Cannot be calculated if no events in control group",
              "Not symmetrical",
              "Can be unstable with rare events"
            ),
            cochrane_recommendation = "Preferred for prospective studies with moderate event rates"
          ),
          
          risk_difference = list(
            when_to_use = c(
              "When absolute effects are important",
              "For calculating NNT",
              "When baseline risks are similar"
            ),
            interpretation = "Absolute difference in risk between groups",
            advantages = c(
              "Shows absolute benefit/harm",
              "Can calculate NNT directly",
              "Easy to understand"
            ),
            disadvantages = c(
              "Highly dependent on baseline risk",
              "Less generalizable across populations",
              "Can be zero even when relative effect exists"
            ),
            cochrane_recommendation = "Use alongside relative measures for complete picture"
          )
        ),
        
        decision_algorithm = function(event_rate, study_type, clinical_context) {
          if (event_rate < 0.1) {
            return("odds_ratio")  # OR for rare events
          } else if (study_type == "case_control") {
            return("odds_ratio")  # OR required for case-control
          } else if (clinical_context == "communication") {
            return("risk_ratio")  # RR for clinical communication
          } else {
            return("risk_ratio")  # Default to RR
          }
        }
      ),
      
      continuous_outcomes = list(
        definition = "Outcomes measured on a numerical scale",
        
        measures = list(
          mean_difference = list(
            when_to_use = c(
              "Same outcome measured on same scale",
              "Clinically meaningful units",
              "When preserving original units is important"
            ),
            examples = c(
              "Blood pressure in mmHg",
              "Weight loss in kg",
              "Pain on 0-10 VAS scale"
            ),
            cochrane_recommendation = "Preferred when all studies use the same measurement scale"
          ),
          
          standardized_mean_difference = list(
            when_to_use = c(
              "Same outcome on different scales",
              "Different instruments measuring same construct",
              "When comparing across different measures"
            ),
            examples = c(
              "Depression measured by different scales (HAM-D, BDI, MADRS)",
              "Quality of life with different instruments",
              "Pain measured on different scales"
            ),
            interpretation_guide = list(
              small = "SMD around 0.2",
              medium = "SMD around 0.5",
              large = "SMD around 0.8"
            ),
            cochrane_recommendation = "Use when studies measure the same concept with different instruments"
          )
        ),
        
        decision_algorithm = function(scales_used, clinical_importance) {
          if (length(unique(scales_used)) == 1) {
            return("mean_difference")
          } else {
            return("standardized_mean_difference")
          }
        }
      ),
      
      time_to_event_outcomes = list(
        definition = "Outcomes measuring time until an event occurs",
        measure = "hazard_ratio",
        cochrane_recommendation = "Use hazard ratios for survival data, ensuring proper censoring handling"
      )
    ),
    
    # Step 3: Model Selection Decision Tree
    model_selection = list(
      question = "Which statistical model should be used?",
      cochrane_ref = "Handbook Section 10.10: Addressing heterogeneity",
      
      fixed_effect = list(
        assumption = "One true effect size underlies all studies",
        when_to_use = c(
          "Studies are functionally identical",
          "Very low heterogeneity (I² < 25%)",
          "Generalizing only to identical populations"
        ),
        advantages = c(
          "More statistical power",
          "Narrower confidence intervals",
          "Simpler interpretation"
        ),
        disadvantages = c(
          "Unrealistic assumption often",
          "Can give false precision",
          "Ignores between-study variation"
        ),
        cochrane_position = "Rarely appropriate for clinical studies due to inherent differences"
      ),
      
      random_effects = list(
        assumption = "Effect sizes vary across studies following a distribution",
        when_to_use = c(
          "Clinical/methodological diversity exists",
          "Moderate to high heterogeneity",
          "Generalizing to broader population"
        ),
        advantages = c(
          "Accounts for between-study variation",
          "More conservative (wider CIs)",
          "More realistic for most clinical questions"
        ),
        disadvantages = c(
          "Requires more studies for stability",
          "Can give undue weight to small studies",
          "More complex interpretation"
        ),
        cochrane_position = "Generally preferred for clinical interventions due to inherent diversity"
      ),
      
      decision_algorithm = function(i_squared, n_studies, clinical_diversity) {
        if (n_studies < 5) {
          return(list(
            model = "avoid_meta_analysis",
            reason = "Too few studies for reliable synthesis",
            alternative = "narrative_synthesis"
          ))
        } else if (i_squared < 25 && !clinical_diversity) {
          return(list(
            model = "fixed_effect",
            reason = "Low heterogeneity and similar studies",
            caveat = "Consider if assumption is realistic"
          ))
        } else {
          return(list(
            model = "random_effects",
            reason = "Accounts for heterogeneity",
            method = "REML or DerSimonian-Laird"
          ))
        }
      }
    ),
    
    # Step 4: Heterogeneity Assessment Decision Tree
    heterogeneity_assessment = list(
      question = "How should heterogeneity be assessed and addressed?",
      cochrane_ref = "Handbook Chapter 10: Analysing data and undertaking meta-analyses",
      
      detection = list(
        visual = list(
          method = "Forest plot inspection",
          look_for = c(
            "Non-overlapping confidence intervals",
            "Studies on opposite sides of null",
            "One study very different from others"
          )
        ),
        
        statistical = list(
          i_squared = list(
            interpretation = list(
              "0-25%" = list(
                label = "Low heterogeneity",
                action = "May proceed with meta-analysis",
                consideration = "Check if studies are truly similar"
              ),
              "25-50%" = list(
                label = "Moderate heterogeneity",
                action = "Explore sources, use random-effects",
                consideration = "Subgroup analysis may be warranted"
              ),
              "50-75%" = list(
                label = "Substantial heterogeneity",
                action = "Investigate sources before pooling",
                consideration = "Meta-regression if >10 studies"
              ),
              ">75%" = list(
                label = "Considerable heterogeneity",
                action = "Question whether pooling is appropriate",
                consideration = "May need to not pool, report separately"
              )
            ),
            limitations = c(
              "Depends on study size and number",
              "Can be 0% even with clinical heterogeneity",
              "Uncertainty with few studies"
            )
          ),
          
          tau_squared = list(
            interpretation = "Variance of true effects",
            clinical_meaning = "Express on same scale as outcome for interpretation",
            use = "Calculate prediction intervals"
          ),
          
          q_test = list(
            interpretation = "Test for presence of heterogeneity",
            limitation = "Low power with few studies",
            cochrane_note = "Do not rely solely on p-value"
          )
        )
      ),
      
      investigation = list(
        subgroup_analysis = list(
          when_appropriate = c(
            "Pre-specified in protocol",
            "≥10 studies available",
            "Clear rationale exists"
          ),
          common_subgroups = c(
            "Dose/intensity of intervention",
            "Duration of follow-up",
            "Baseline severity",
            "Geographic region",
            "Study quality/risk of bias"
          ),
          interpretation_cautions = c(
            "Observational comparisons",
            "Multiple testing issues",
            "Low power within subgroups"
          ),
          statistical_test = "Test for subgroup differences (interaction test)"
        ),
        
        meta_regression = list(
          when_appropriate = c(
            "≥10 studies (preferably more)",
            "Continuous study-level covariate",
            "Exploring dose-response"
          ),
          limitations = c(
            "Ecological fallacy",
            "Confounding at study level",
            "Requires many studies"
          )
        ),
        
        sensitivity_analysis = list(
          purpose = "Test robustness of findings",
          common_analyses = c(
            "Exclude high risk of bias studies",
            "Exclude outliers",
            "Use different effect measures",
            "Use different statistical models",
            "Exclude industry-funded studies"
          ),
          interpretation = "If conclusions change, findings are not robust"
        )
      ),
      
      reporting = list(
        always_report = c(
          "I² with confidence interval",
          "Tau² or Tau",
          "Q statistic with p-value",
          "Prediction interval (random-effects)",
          "Visual display (forest plot)"
        ),
        
        interpretation_guidance = c(
          "Discuss clinical and methodological diversity",
          "Explain investigation of heterogeneity",
          "State impact on conclusions",
          "Consider GRADE certainty downgrade"
        )
      )
    ),
    
    # Step 5: Publication Bias Assessment Decision Tree
    publication_bias_assessment = list(
      question = "How should publication bias be assessed?",
      cochrane_ref = "Handbook Chapter 13: Assessing risk of bias due to missing results",
      
      when_to_assess = list(
        minimum_studies = 10,
        rationale = "Tests have low power with fewer studies",
        exception = "Always consider risk conceptually regardless of number"
      ),
      
      methods = list(
        funnel_plot = list(
          what_it_shows = "Scatter plot of effect size vs precision",
          interpretation = list(
            symmetric = "Suggests no publication bias (but not proof)",
            asymmetric = "May indicate bias (but other causes exist)"
          ),
          other_causes_of_asymmetry = c(
            "True heterogeneity",
            "Methodological quality",
            "Chance",
            "Choice of effect measure",
            "Different populations"
          ),
          cochrane_guidance = "Visual inspection subjective; use statistical tests"
        ),
        
        statistical_tests = list(
          egger_test = list(
            use_for = "Continuous outcomes or log-odds ratios",
            limitation = "Can give false positives with heterogeneity",
            minimum_studies = 10
          ),
          
          begg_test = list(
            use_for = "Rank correlation test",
            limitation = "Lower power than Egger's test",
            minimum_studies = 10
          ),
          
          harbord_test = list(
            use_for = "Binary outcomes with OR",
            advantage = "Less affected by heterogeneity than Egger",
            minimum_studies = 10
          ),
          
          peters_test = list(
            use_for = "Binary outcomes with OR/RR",
            advantage = "Good for rare events",
            minimum_studies = 10
          )
        ),
        
        adjustment_methods = list(
          trim_and_fill = list(
            what_it_does = "Imputes 'missing' studies",
            interpretation = "Sensitivity analysis, not primary result",
            limitation = "Assumes specific bias mechanism"
          ),
          
          selection_models = list(
            what_it_does = "Models probability of publication",
            when_to_use = "Advanced analysis with many studies",
            limitation = "Complex, requires expertise"
          )
        )
      ),
      
      decision_algorithm = function(n_studies, outcome_type, event_rate = NULL) {
        if (n_studies < 10) {
          return(list(
            test = "none",
            reason = "Too few studies",
            action = "Discuss risk qualitatively"
          ))
        } else if (outcome_type == "continuous") {
          return(list(
            test = "egger_test",
            visual = "funnel_plot",
            sensitivity = "trim_and_fill"
          ))
        } else if (outcome_type == "binary" && event_rate < 0.1) {
          return(list(
            test = "peters_test",
            visual = "funnel_plot",
            reason = "Better for rare events"
          ))
        } else {
          return(list(
            test = "harbord_test",
            visual = "funnel_plot",
            sensitivity = "trim_and_fill"
          ))
        }
      },
      
      reporting = list(
        always_discuss = "Risk of publication bias regardless of tests",
        if_bias_suspected = c(
          "Discuss impact on conclusions",
          "Consider GRADE downgrade",
          "Report adjusted estimates as sensitivity",
          "Discuss search comprehensiveness"
        )
      )
    ),
    
    # Step 6: Quality Assessment Integration
    quality_assessment = list(
      question = "How should study quality affect the analysis?",
      cochrane_ref = "Handbook Chapter 8: Assessing risk of bias",
      
      rob_tools = list(
        rct = list(
          tool = "RoB 2",
          domains = c(
            "Randomization process",
            "Deviations from intended interventions",
            "Missing outcome data",
            "Measurement of the outcome",
            "Selection of reported result"
          ),
          overall_judgment = c("Low risk", "Some concerns", "High risk")
        ),
        
        non_rct = list(
          tool = "ROBINS-I",
          domains = c(
            "Confounding",
            "Selection of participants",
            "Classification of interventions",
            "Deviations from intended interventions",
            "Missing data",
            "Measurement of outcomes",
            "Selection of reported results"
          ),
          overall_judgment = c("Low", "Moderate", "Serious", "Critical")
        )
      ),
      
      incorporation_methods = list(
        sensitivity_analysis = list(
          approach = "Exclude high risk studies",
          when = "Primary analysis includes all studies",
          interpretation = "Check if conclusions change"
        ),
        
        subgroup_analysis = list(
          approach = "Analyze by risk of bias level",
          when = "Sufficient studies in each category",
          test = "Test for subgroup differences"
        ),
        
        quality_weights = list(
          approach = "Weight by quality score",
          cochrane_position = "Not recommended",
          reason = "Quality scores can be misleading"
        ),
        
        restriction = list(
          approach = "Include only low risk studies",
          when = "Sufficient low risk studies exist",
          disadvantage = "Reduces power and generalizability"
        )
      ),
      
      grade_assessment = list(
        starting_certainty = list(
          RCT = "High",
          observational = "Low"
        ),
        
        downgrade_factors = list(
          risk_of_bias = "-1 or -2 levels",
          inconsistency = "-1 or -2 levels for heterogeneity",
          indirectness = "-1 or -2 levels",
          imprecision = "-1 or -2 levels for wide CIs",
          publication_bias = "-1 or -2 levels"
        ),
        
        upgrade_factors = list(
          large_effect = "+1 or +2 levels",
          dose_response = "+1 level",
          plausible_confounding = "+1 level"
        )
      )
    ),
    
    # Step 7: Reporting Guidelines
    reporting_guidelines = list(
      prisma = list(
        sections = c(
          "Title: Identify as systematic review/meta-analysis",
          "Abstract: Structured summary",
          "Introduction: Rationale and objectives",
          "Methods: Protocol, eligibility, search, selection, data extraction, risk of bias, synthesis",
          "Results: Study selection, characteristics, risk of bias, synthesis results",
          "Discussion: Summary, limitations, conclusions"
        ),
        
        key_items = c(
          "PROSPERO registration number",
          "Full search strategy",
          "Study selection flow diagram",
          "Risk of bias assessment",
          "Forest plots for all outcomes",
          "GRADE summary of findings table"
        )
      )
    )
  )
  
  return(decision_tree)
}

#' Get specific guidance based on analysis context
#' @param topic The specific topic needing guidance
#' @param context Current analysis parameters
#' @return Detailed guidance and recommendations
get_contextual_guidance <- function(topic, context = list()) {
  
  guidance <- list()
  
  # Provide specific guidance based on the topic
  if (topic == "heterogeneity_interpretation") {
    i_squared <- context$i_squared %||% 50
    n_studies <- context$n_studies %||% 10
    
    guidance$interpretation <- interpret_heterogeneity(i_squared, n_studies)
    guidance$next_steps <- suggest_heterogeneity_investigation(i_squared, n_studies)
    guidance$reporting <- heterogeneity_reporting_checklist()
    
  } else if (topic == "model_choice") {
    guidance$decision <- model_selection_logic(
      context$i_squared,
      context$n_studies,
      context$clinical_diversity
    )
    guidance$justification <- generate_model_justification(guidance$decision)
    
  } else if (topic == "effect_measure_choice") {
    guidance$recommendation <- select_effect_measure(
      context$outcome_type,
      context$event_rate,
      context$study_designs
    )
    guidance$rationale <- explain_effect_measure_choice(guidance$recommendation)
    
  } else if (topic == "publication_bias_testing") {
    guidance$appropriate_test <- select_bias_test(
      context$n_studies,
      context$outcome_type,
      context$effect_measure
    )
    guidance$interpretation_cautions <- bias_test_limitations()
    
  } else if (topic == "subgroup_analysis_planning") {
    guidance$feasibility <- assess_subgroup_feasibility(
      context$n_studies,
      context$planned_subgroups
    )
    guidance$statistical_approach <- subgroup_analysis_methods()
    guidance$interpretation_framework <- subgroup_interpretation_guide()
  }
  
  return(guidance)
}

#' Helper function to interpret heterogeneity
interpret_heterogeneity <- function(i_squared, n_studies) {
  interpretation <- list()
  
  # Basic interpretation
  if (i_squared < 25) {
    interpretation$level <- "low"
    interpretation$meaning <- "Heterogeneity might not be important"
  } else if (i_squared < 50) {
    interpretation$level <- "moderate"
    interpretation$meaning <- "Moderate heterogeneity present"
  } else if (i_squared < 75) {
    interpretation$level <- "substantial"
    interpretation$meaning <- "Substantial heterogeneity present"
  } else {
    interpretation$level <- "considerable"
    interpretation$meaning <- "Considerable heterogeneity present"
  }
  
  # Confidence in interpretation
  if (n_studies < 5) {
    interpretation$confidence <- "very_low"
    interpretation$caveat <- "Very few studies make heterogeneity assessment unreliable"
  } else if (n_studies < 10) {
    interpretation$confidence <- "low"
    interpretation$caveat <- "Limited studies reduce confidence in heterogeneity assessment"
  } else {
    interpretation$confidence <- "moderate"
    interpretation$caveat <- "Reasonable number of studies for heterogeneity assessment"
  }
  
  # Clinical importance
  interpretation$clinical_importance <- paste(
    "Even with", interpretation$level, "statistical heterogeneity,",
    "consider whether studies are clinically similar enough to combine"
  )
  
  return(interpretation)
}

#' Suggest investigation approaches for heterogeneity
suggest_heterogeneity_investigation <- function(i_squared, n_studies) {
  suggestions <- list()
  
  if (i_squared > 50) {
    if (n_studies >= 10) {
      suggestions$primary <- "meta_regression"
      suggestions$variables <- c(
        "Dose/intensity of intervention",
        "Duration of treatment",
        "Baseline severity",
        "Year of publication",
        "Risk of bias level"
      )
    } else {
      suggestions$primary <- "subgroup_analysis"
      suggestions$note <- "Limited studies restrict investigation options"
    }
    
    suggestions$always_do <- c(
      "Visual inspection of forest plot",
      "Check for outliers",
      "Review study characteristics table",
      "Consider clinical/methodological differences"
    )
    
    suggestions$sensitivity <- c(
      "Remove outliers",
      "Exclude high risk of bias studies",
      "Use different effect measures",
      "Try fixed-effect model for comparison"
    )
  }
  
  return(suggestions)
}

#' Generate model selection logic
model_selection_logic <- function(i_squared, n_studies, clinical_diversity) {
  if (n_studies < 3) {
    return("no_pooling")
  }
  
  if (n_studies < 5) {
    return("narrative_synthesis_preferred")
  }
  
  if (i_squared < 25 && !clinical_diversity) {
    return("fixed_effect_possible")
  }
  
  return("random_effects_recommended")
}

#' Generate justification for model selection decision
#' @param decision The model decision from model_selection_logic
#' @return Justification text explaining the decision
generate_model_justification <- function(decision) {
  justifications <- list(
    no_pooling = paste(
      "Meta-analysis is not recommended due to insufficient number of studies.",
      "With fewer than 3 studies, statistical pooling is unreliable and may",
      "produce misleading results. Individual study results should be presented",
      "separately with a narrative description of findings."
    ),
    
    narrative_synthesis_preferred = paste(
      "A narrative synthesis is preferred over meta-analysis due to the limited",
      "number of studies (fewer than 5). Statistical pooling with so few studies",
      "may be unstable and heterogeneity estimates unreliable. A structured",
      "narrative approach following synthesis without meta-analysis (SWiM)",
      "guidelines is recommended."
    ),
    
    fixed_effect_possible = paste(
      "A fixed-effect model may be appropriate given the low statistical",
      "heterogeneity (I² < 25%) and absence of clinical diversity. This assumes",
      "all studies estimate the same underlying effect. However, carefully",
      "consider whether this assumption is realistic given the nature of the",
      "intervention and populations studied."
    ),
    
    random_effects_recommended = paste(
      "A random-effects model is recommended to account for between-study",
      "heterogeneity. This model assumes that the true effects in studies are",
      "not identical but follow a distribution. This is typically more",
      "appropriate for clinical interventions where some variation between",
      "studies is expected. Use REML or DerSimonian-Laird estimation method."
    )
  )
  
  # Return the justification or a default message if decision not found
  return(justifications[[decision]] %||%
         "Unable to generate justification for the specified model decision.")
}

#' Null coalescing operator
`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}

#' Generate heterogeneity reporting checklist
#' @return List of items to report regarding heterogeneity
heterogeneity_reporting_checklist <- function() {
  list(
    statistical_measures = c(
      "Report I² statistic with 95% confidence interval",
      "Report Tau² (between-study variance) on the same scale as the outcome",
      "Report Q statistic with degrees of freedom and p-value",
      "Include prediction interval for random-effects models"
    ),
    visual_presentation = c(
      "Provide forest plot with study weights visible",
      "Consider subgroup forest plots if applicable",
      "Include sensitivity analysis plots if performed"
    ),
    narrative_elements = c(
      "Describe clinical and methodological diversity among studies",
      "Explain investigation methods used (subgroup, meta-regression)",
      "Discuss impact of heterogeneity on conclusions",
      "State whether heterogeneity affects certainty of evidence (GRADE)"
    )
  )
}

#' Select appropriate effect measure based on context
#' @param outcome_type Type of outcome (binary, continuous, time_to_event)
#' @param event_rate Event rate for binary outcomes
#' @param study_designs Types of study designs included
#' @return Recommended effect measure
select_effect_measure <- function(outcome_type, event_rate = NULL, study_designs = NULL) {
  if (outcome_type == "binary") {
    if (!is.null(event_rate) && event_rate < 0.1) {
      return("odds_ratio")
    } else if ("case_control" %in% study_designs) {
      return("odds_ratio")
    } else {
      return("risk_ratio")
    }
  } else if (outcome_type == "continuous") {
    return("mean_difference")  # or "standardized_mean_difference" based on scale consistency
  } else if (outcome_type == "time_to_event") {
    return("hazard_ratio")
  }
  
  return("unclear")
}

#' Explain the rationale for effect measure choice
#' @param effect_measure The chosen effect measure
#' @return Explanation text
explain_effect_measure_choice <- function(effect_measure) {
  explanations <- list(
    odds_ratio = paste(
      "Odds ratio selected because it is appropriate for case-control studies",
      "or when events are rare (<10%). OR has favorable mathematical properties",
      "but can be difficult to interpret clinically."
    ),
    risk_ratio = paste(
      "Risk ratio selected as it provides intuitive interpretation for",
      "prospective studies. RR directly measures the probability of an event",
      "in the intervention group relative to the control group."
    ),
    risk_difference = paste(
      "Risk difference selected to show absolute effect size. This measure",
      "is useful for calculating number needed to treat (NNT) and provides",
      "information about the public health impact of the intervention."
    ),
    mean_difference = paste(
      "Mean difference selected as all studies use the same measurement scale.",
      "This preserves the original units which aids clinical interpretation."
    ),
    standardized_mean_difference = paste(
      "Standardized mean difference selected because studies use different",
      "scales to measure the same construct. SMD allows comparison across",
      "different measurement instruments."
    ),
    hazard_ratio = paste(
      "Hazard ratio selected for time-to-event data. HR accounts for",
      "censoring and provides information about the instantaneous risk",
      "over the entire follow-up period."
    )
  )
  
  return(explanations[[effect_measure]] %||%
         "Unable to explain the effect measure choice.")
}

#' Select appropriate publication bias test
#' @param n_studies Number of studies
#' @param outcome_type Type of outcome
#' @param effect_measure Effect measure being used
#' @return Recommended test for publication bias
select_bias_test <- function(n_studies, outcome_type, effect_measure = NULL) {
  if (n_studies < 10) {
    return(list(
      test = "none",
      reason = "Too few studies for reliable testing",
      recommendation = "Discuss publication bias risk qualitatively"
    ))
  }
  
  if (outcome_type == "continuous") {
    return(list(
      test = "egger",
      reason = "Egger's test is appropriate for continuous outcomes"
    ))
  } else if (outcome_type == "binary") {
    if (effect_measure == "odds_ratio") {
      return(list(
        test = "harbord",
        reason = "Harbord test is less affected by heterogeneity for OR"
      ))
    } else {
      return(list(
        test = "peters",
        reason = "Peters test is appropriate for binary outcomes with RR"
      ))
    }
  }
  
  return(list(
    test = "egger",
    reason = "Default to Egger's test"
  ))
}

#' Provide limitations of publication bias tests
#' @return List of important limitations
bias_test_limitations <- function() {
  list(
    general = c(
      "All tests have low power with fewer than 10 studies",
      "Tests may detect small-study effects rather than publication bias",
      "Asymmetry can be caused by heterogeneity, not just publication bias"
    ),
    specific = list(
      egger = "Can give false positives when there is substantial heterogeneity",
      begg = "Has lower statistical power than Egger's test",
      harbord = "Specifically designed for odds ratios, less affected by heterogeneity",
      peters = "Better for binary outcomes with low event rates"
    ),
    interpretation = c(
      "A significant test does not prove publication bias exists",
      "A non-significant test does not prove absence of bias",
      "Consider multiple sources of funnel plot asymmetry",
      "Use as one piece of evidence alongside other considerations"
    )
  )
}

#' Assess feasibility of subgroup analysis
#' @param n_studies Total number of studies
#' @param planned_subgroups Number or list of planned subgroups
#' @return Assessment of feasibility
assess_subgroup_feasibility <- function(n_studies, planned_subgroups = NULL) {
  n_subgroups <- if (is.numeric(planned_subgroups)) {
    planned_subgroups
  } else if (is.list(planned_subgroups)) {
    length(planned_subgroups)
  } else {
    0
  }
  
  if (n_studies < 10) {
    return(list(
      feasible = FALSE,
      reason = "Too few studies for reliable subgroup analysis",
      recommendation = "Consider as exploratory analysis only"
    ))
  }
  
  studies_per_subgroup <- n_studies / max(n_subgroups, 2)
  
  if (studies_per_subgroup < 4) {
    return(list(
      feasible = FALSE,
      reason = "Too few studies per subgroup for meaningful analysis",
      recommendation = "Reduce number of subgroups or treat as hypothesis-generating"
    ))
  }
  
  return(list(
    feasible = TRUE,
    reason = "Adequate number of studies for planned subgroups",
    recommendation = "Ensure subgroups were pre-specified in protocol"
  ))
}

#' Provide methods for subgroup analysis
#' @return List of methodological guidance
subgroup_analysis_methods <- function() {
  list(
    statistical_approach = list(
      test = "Test for subgroup differences (interaction test)",
      interpretation = "Focus on the test for interaction, not within-subgroup effects",
      software = "Use meta-regression or subgroup analysis functions in meta packages"
    ),
    best_practices = c(
      "Pre-specify subgroups in protocol to avoid data dredging",
      "Limit number of subgroups to maintain statistical power",
      "Use within-study information when available",
      "Consider biological plausibility of subgroup effects"
    ),
    common_pitfalls = c(
      "Multiple testing without adjustment",
      "Post-hoc subgroup identification",
      "Over-interpretation of subgroup findings",
      "Ignoring the play of chance with small subgroups"
    ),
    reporting = c(
      "Report all planned subgroup analyses, not just significant ones",
      "Provide test for interaction with confidence interval",
      "Discuss limitations and exploratory nature if post-hoc",
      "Consider clinical importance alongside statistical significance"
    )
  )
}

#' Provide interpretation framework for subgroup analysis
#' @return Structured guidance for interpretation
subgroup_interpretation_guide <- function() {
  list(
    credibility_criteria = c(
      "Was the subgroup analysis pre-specified?",
      "Is the subgroup effect consistent across studies?",
      "Was the test for interaction statistically significant?",
      "Is there a strong biological rationale?",
      "Is the subgroup effect consistent across related outcomes?"
    ),
    interpretation_levels = list(
      high_credibility = "Pre-specified, significant interaction, biological rationale",
      moderate_credibility = "Some criteria met, treat as hypothesis-generating",
      low_credibility = "Post-hoc finding, no clear rationale, likely spurious"
    ),
    clinical_relevance = c(
      "Consider magnitude of subgroup difference",
      "Assess if difference would change clinical practice",
      "Evaluate consistency with other evidence",
      "Consider feasibility of applying in practice"
    ),
    reporting_guidance = c(
      "Be transparent about exploratory vs confirmatory nature",
      "Avoid overemphasis on subgroup findings in conclusions",
      "Suggest further research if finding appears important",
      "Consider GRADE approach for subgroup-specific recommendations"
    )
  )
}

#' Export guidance for LLM consumption
#' @param format Output format (json, text, structured)
#' @return Formatted guidance for LLM
export_guidance_for_llm <- function(format = "structured") {
  
  # Get complete decision tree
  decision_tree <- get_meta_analysis_decision_tree()
  
  if (format == "json") {
    return(jsonlite::toJSON(decision_tree, pretty = TRUE, auto_unbox = TRUE))
    
  } else if (format == "structured") {
    # Create structured prompt for LLM
    prompt <- list(
      system_role = "You are a meta-analysis expert following Cochrane Handbook guidelines.",
      
      knowledge_base = decision_tree,
      
      decision_process = "For each analysis decision:
        1. Identify the relevant section in the decision tree
        2. Apply the decision algorithm with current context
        3. Provide Cochrane-based justification
        4. Suggest next steps based on the result
        5. Flag any limitations or cautions",
      
      output_format = "Provide structured recommendations with:
        - Decision made
        - Cochrane reference
        - Rationale
        - Alternatives considered
        - Limitations
        - Next steps"
    )
    
    return(prompt)
    
  } else {
    # Plain text format
    return(capture.output(str(decision_tree)))
  }
}

#' Check analysis decisions against Cochrane standards
#' @param analysis_plan The planned analysis approach
#' @return Validation results with recommendations
validate_against_cochrane <- function(analysis_plan) {
  validation <- list()
  issues <- list()
  
  # Check effect measure choice
  if (!is.null(analysis_plan$effect_measure)) {
    if (analysis_plan$outcome_type == "binary" && 
        analysis_plan$effect_measure == "OR" && 
        analysis_plan$event_rate > 0.2) {
      issues$effect_measure <- "Odds ratios can be misleading with common events (>20%). Consider risk ratio."
    }
  }
  
  # Check model choice
  if (!is.null(analysis_plan$model)) {
    if (analysis_plan$model == "fixed" && analysis_plan$clinical_diversity) {
      issues$model <- "Fixed-effect model inappropriate with clinical diversity. Use random-effects."
    }
  }
  
  # Check heterogeneity plan
  if (!is.null(analysis_plan$n_studies)) {
    if (analysis_plan$n_studies < 10 && analysis_plan$planned_metaregression) {
      issues$metaregression <- "Meta-regression unreliable with <10 studies. Consider subgroup analysis instead."
    }
  }
  
  # Check publication bias plan
  if (!is.null(analysis_plan$n_studies)) {
    if (analysis_plan$n_studies < 10 && analysis_plan$test_publication_bias) {
      issues$publication_bias <- "Publication bias tests unreliable with <10 studies. Discuss qualitatively."
    }
  }
  
  validation$issues <- issues
  validation$is_valid <- length(issues) == 0
  validation$recommendations <- generate_recommendations(issues)
  
  return(validation)
}

#' Generate recommendations based on identified issues
generate_recommendations <- function(issues) {
  recommendations <- list()
  
  for (issue_name in names(issues)) {
    recommendations[[issue_name]] <- list(
      issue = issues[[issue_name]],
      action = suggest_alternative_approach(issue_name),
      cochrane_reference = get_relevant_cochrane_section(issue_name)
    )
  }
  
  return(recommendations)
}

#' Suggest alternative approaches for identified issues
suggest_alternative_approach <- function(issue_type) {
  alternatives <- list(
    effect_measure = "Use risk ratio or risk difference for common events",
    model = "Switch to random-effects model with REML estimation",
    metaregression = "Use pre-specified subgroup analyses instead",
    publication_bias = "Provide qualitative discussion of publication bias risk"
  )
  
  return(alternatives[[issue_type]] %||% "Consult Cochrane Handbook for guidance")
}

#' Get relevant Cochrane Handbook section
get_relevant_cochrane_section <- function(topic) {
  sections <- list(
    effect_measure = "Section 6.4: Effect measures for dichotomous outcomes",
    model = "Section 10.10.4: Incorporating heterogeneity into random-effects models",
    metaregression = "Section 10.11: Investigating heterogeneity",
    publication_bias = "Chapter 13: Assessing risk of bias due to missing results",
    heterogeneity = "Section 10.10.2: Identifying and measuring heterogeneity",
    subgroup = "Section 10.11.3: Subgroup analyses",
    sensitivity = "Section 10.14: Sensitivity analyses",
    quality = "Chapter 8: Assessing risk of bias in included studies"
  )
  
  return(sections[[topic]] %||% "See Cochrane Handbook for Systematic Reviews")
}

# Export the enhanced guidance system
message("Cochrane Enhanced Guidance System loaded successfully")
message("Use get_meta_analysis_decision_tree() for complete decision framework")
message("Use get_contextual_guidance(topic, context) for specific guidance")
message("Use validate_against_cochrane(analysis_plan) to check decisions")

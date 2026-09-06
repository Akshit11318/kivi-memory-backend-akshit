# Kivi eval results

Profiles: off, exact, phonetic, llm

## Summary

| profile | pass | fail | skipped | error | useful | unnecessary | incorrect | expected_abstain | unexpected_abstain | model_calls | total_latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| off | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 28 | 0 | 0 | 0.04 |
| exact | 26 | 2 | 0 | 0 | 11 | 0 | 0 | 15 | 2 | 0 | 11.88 |
| phonetic | 26 | 2 | 0 | 0 | 12 | 0 | 0 | 14 | 2 | 0 | 11.96 |
| llm | 0 | 0 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |
| foo | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |

## Cases

| case | family | rows | profile | status | expected | actual | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| case_01_useful_apply_brief | useful_apply | 2 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_01_useful_apply_brief | useful_apply | 2 | exact | PASS | APPLY | APPLY | applied Aaditya, Kivi |
| case_01_useful_apply_brief | useful_apply | 2 | phonetic | PASS | APPLY | APPLY | applied Aaditya, Kivi |
| case_01_useful_apply_brief | useful_apply | 2 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_02_useful_apply_two_names | two_names | 2 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_02_useful_apply_two_names | two_names | 2 | exact | FAIL | APPLY | ABSTAIN | context_mismatch, no_memory |
| case_02_useful_apply_two_names | two_names | 2 | phonetic | FAIL | APPLY | ABSTAIN | context_mismatch, no_memory |
| case_02_useful_apply_two_names | two_names | 2 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_03_deliberate_noop_empty_store | noop | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_03_deliberate_noop_empty_store | noop | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_03_deliberate_noop_empty_store | noop | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_03_deliberate_noop_empty_store | noop | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_04_irrelevant_memory_store | noop | 2 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_04_irrelevant_memory_store | noop | 2 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_04_irrelevant_memory_store | noop | 2 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_04_irrelevant_memory_store | noop | 2 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_05_weak_confidence_abstain | abstain_weak | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_05_weak_confidence_abstain | abstain_weak | 1 | exact | PASS | ABSTAIN | ABSTAIN | low_confidence, no_memory |
| case_05_weak_confidence_abstain | abstain_weak | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | low_confidence, no_memory |
| case_05_weak_confidence_abstain | abstain_weak | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_06_observe_no_assertion | learner_gate | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_06_observe_no_assertion | learner_gate | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_06_observe_no_assertion | learner_gate | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_06_observe_no_assertion | learner_gate | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_07_content_edit_rejected | learner_gate | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_07_content_edit_rejected | learner_gate | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_07_content_edit_rejected | learner_gate | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_07_content_edit_rejected | learner_gate | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_08_conflicting_canonicals | conflict | 2 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_08_conflicting_canonicals | conflict | 2 | exact | PASS | ABSTAIN | ABSTAIN | conflicting_canonicals, no_memory |
| case_08_conflicting_canonicals | conflict | 2 | phonetic | PASS | ABSTAIN | ABSTAIN | conflicting_canonicals, no_memory |
| case_08_conflicting_canonicals | conflict | 2 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_09_empty_garbage_input | edge_robustness | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_09_empty_garbage_input | edge_robustness | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_09_empty_garbage_input | edge_robustness | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_09_empty_garbage_input | edge_robustness | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_10_phonetic_only_retrieval | phonetic_only | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_10_phonetic_only_retrieval | phonetic_only | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_10_phonetic_only_retrieval | phonetic_only | 1 | phonetic | PASS | APPLY | APPLY | applied Kivi |
| case_10_phonetic_only_retrieval | phonetic_only | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_11_word_boundary | boundary | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_11_word_boundary | boundary | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_11_word_boundary | boundary | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_11_word_boundary | boundary | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_12_cold_start_reset | reset_state | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_12_cold_start_reset | reset_state | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_12_cold_start_reset | reset_state | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_12_cold_start_reset | reset_state | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_13_duplicate_observe_idempotent | idempotency | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_13_duplicate_observe_idempotent | idempotency | 1 | exact | PASS | APPLY | APPLY | applied Laxmi |
| case_13_duplicate_observe_idempotent | idempotency | 1 | phonetic | PASS | APPLY | APPLY | applied Laxmi |
| case_13_duplicate_observe_idempotent | idempotency | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_14_already_canonical_abstain | noop | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_14_already_canonical_abstain | noop | 1 | exact | PASS | ABSTAIN | ABSTAIN | already_canonical, no_memory |
| case_14_already_canonical_abstain | noop | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | already_canonical, no_memory |
| case_14_already_canonical_abstain | noop | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_15_multi_user_isolation | isolation | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_15_multi_user_isolation | isolation | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_15_multi_user_isolation | isolation | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_15_multi_user_isolation | isolation | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_16_code_switch_hinglish | code_switch | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_16_code_switch_hinglish | code_switch | 1 | exact | PASS | APPLY | APPLY | applied Diksha |
| case_16_code_switch_hinglish | code_switch | 1 | phonetic | PASS | APPLY | APPLY | applied Diksha |
| case_16_code_switch_hinglish | code_switch | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_17_token_count_mismatch_alignment | alignment_stress | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_17_token_count_mismatch_alignment | alignment_stress | 1 | exact | PASS | APPLY | APPLY | applied Tanmaay |
| case_17_token_count_mismatch_alignment | alignment_stress | 1 | phonetic | PASS | APPLY | APPLY | applied Tanmaay |
| case_17_token_count_mismatch_alignment | alignment_stress | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_18_punctuation_attached_clitics | punctuation | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_18_punctuation_attached_clitics | punctuation | 1 | exact | PASS | APPLY | APPLY | applied Kivi |
| case_18_punctuation_attached_clitics | punctuation | 1 | phonetic | PASS | APPLY | APPLY | applied Kivi |
| case_18_punctuation_attached_clitics | punctuation | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_19_multiple_mentions_one_sentence | multi_mention | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_19_multiple_mentions_one_sentence | multi_mention | 1 | exact | PASS | APPLY | APPLY | applied Pratik |
| case_19_multiple_mentions_one_sentence | multi_mention | 1 | phonetic | PASS | APPLY | APPLY | applied Pratik |
| case_19_multiple_mentions_one_sentence | multi_mention | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_20_sentence_initial_case | casing | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_20_sentence_initial_case | casing | 1 | exact | FAIL | APPLY | ABSTAIN | context_mismatch, no_memory |
| case_20_sentence_initial_case | casing | 1 | phonetic | FAIL | APPLY | ABSTAIN | context_mismatch, no_memory |
| case_20_sentence_initial_case | casing | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_21_short_token_phonetic_fp | phonetic_guard | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_21_short_token_phonetic_fp | phonetic_guard | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_21_short_token_phonetic_fp | phonetic_guard | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_21_short_token_phonetic_fp | phonetic_guard | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_22_merge_dictionary_forms | form_merge | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_22_merge_dictionary_forms | form_merge | 1 | exact | PASS | APPLY | APPLY | applied Kivi |
| case_22_merge_dictionary_forms | form_merge | 1 | phonetic | PASS | APPLY | APPLY | applied Kivi |
| case_22_merge_dictionary_forms | form_merge | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_23_reinforcement_crossing_threshold | threshold_crossing | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_23_reinforcement_crossing_threshold | threshold_crossing | 1 | exact | PASS | APPLY | APPLY | applied Chowdhury |
| case_23_reinforcement_crossing_threshold | threshold_crossing | 1 | phonetic | PASS | APPLY | APPLY | applied Chowdhury |
| case_23_reinforcement_crossing_threshold | threshold_crossing | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_24_formatter_introduced_error | formatter_error | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_24_formatter_introduced_error | formatter_error | 1 | exact | PASS | APPLY | APPLY | applied Sreenivas |
| case_24_formatter_introduced_error | formatter_error | 1 | phonetic | PASS | APPLY | APPLY | applied Sreenivas |
| case_24_formatter_introduced_error | formatter_error | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_25_confidence_boundary_075 | boundary | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_25_confidence_boundary_075 | boundary | 1 | exact | PASS | APPLY | APPLY | applied Kivi |
| case_25_confidence_boundary_075 | boundary | 1 | phonetic | PASS | APPLY | APPLY | applied Kivi |
| case_25_confidence_boundary_075 | boundary | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_26_refuse_homophone_grammar | learner_gate | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_26_refuse_homophone_grammar | learner_gate | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_26_refuse_homophone_grammar | learner_gate | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_26_refuse_homophone_grammar | learner_gate | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_27_invalid_profile_error | profile_validation | 0 | foo | PASS | ERROR | ERROR | 'foo' not in ('off', 'exact', 'phonetic', 'llm') |
| case_28_context_cues_apply | context_cues | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_28_context_cues_apply | context_cues | 1 | exact | PASS | APPLY | APPLY | applied Kivi |
| case_28_context_cues_apply | context_cues | 1 | phonetic | PASS | APPLY | APPLY | applied Kivi |
| case_28_context_cues_apply | context_cues | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_29_context_cues_abstain | context_cues | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_29_context_cues_abstain | context_cues | 1 | exact | PASS | ABSTAIN | ABSTAIN | context_mismatch, no_memory |
| case_29_context_cues_abstain | context_cues | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | context_mismatch, no_memory |
| case_29_context_cues_abstain | context_cues | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |

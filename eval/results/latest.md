# Kivi eval results

Profiles: off, exact, phonetic, llm

## Summary

| profile | pass | fail | skipped | error | useful | unnecessary | incorrect | expected_abstain | unexpected_abstain | model_calls | total_latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| off | 71 | 0 | 0 | 0 | 0 | 0 | 0 | 71 | 0 | 0 | 0.04 |
| exact | 69 | 2 | 0 | 0 | 32 | 0 | 0 | 37 | 2 | 0 | 23.80 |
| phonetic | 69 | 2 | 0 | 0 | 38 | 0 | 0 | 31 | 2 | 0 | 25.29 |
| llm | 0 | 0 | 71 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |
| foo | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |

## Assertion coverage

Of 72 cases: 69 assert *why* (reason strings), 69 assert which tokens changed, 69 assert what the learner wrote.

3 case(s) check only decision + text, so they cannot detect a deleted gate: `case_02_useful_apply_two_names`, `case_20_sentence_initial_case`, `case_27_invalid_profile_error`

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
| case_n02_apply_respell_added_consonant | useful_apply | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n02_apply_respell_added_consonant | useful_apply | 1 | exact | PASS | APPLY | APPLY | applied Rajkummar |
| case_n02_apply_respell_added_consonant | useful_apply | 1 | phonetic | PASS | APPLY | APPLY | applied Rajkummar |
| case_n02_apply_respell_added_consonant | useful_apply | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n03_apply_respell_zeroshot_phonetic | phonetic_only | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n03_apply_respell_zeroshot_phonetic | phonetic_only | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n03_apply_respell_zeroshot_phonetic | phonetic_only | 1 | phonetic | PASS | APPLY | APPLY | applied Ayushmann |
| case_n03_apply_respell_zeroshot_phonetic | phonetic_only | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n04_apply_respell_dropped_letter | useful_apply | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n04_apply_respell_dropped_letter | useful_apply | 1 | exact | PASS | APPLY | APPLY | applied Devgn |
| case_n04_apply_respell_dropped_letter | useful_apply | 1 | phonetic | PASS | APPLY | APPLY | applied Devgn |
| case_n04_apply_respell_dropped_letter | useful_apply | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n05_apply_variant_i_to_ee | phonetic_only | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n05_apply_variant_i_to_ee | phonetic_only | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n05_apply_variant_i_to_ee | phonetic_only | 1 | phonetic | PASS | APPLY | APPLY | applied Meera |
| case_n05_apply_variant_i_to_ee | phonetic_only | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n06_apply_variant_u_to_oo | phonetic_only | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n06_apply_variant_u_to_oo | phonetic_only | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n06_apply_variant_u_to_oo | phonetic_only | 1 | phonetic | PASS | APPLY | APPLY | applied Moorthy |
| case_n06_apply_variant_u_to_oo | phonetic_only | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n07_apply_variant_ksh_after_teach | useful_apply | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n07_apply_variant_ksh_after_teach | useful_apply | 1 | exact | PASS | APPLY | APPLY | applied Laxmi |
| case_n07_apply_variant_ksh_after_teach | useful_apply | 1 | phonetic | PASS | APPLY | APPLY | applied Laxmi |
| case_n07_apply_variant_ksh_after_teach | useful_apply | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n08_apply_bengali_surname_variant | useful_apply | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n08_apply_bengali_surname_variant | useful_apply | 1 | exact | PASS | APPLY | APPLY | applied Choudhury |
| case_n08_apply_bengali_surname_variant | useful_apply | 1 | phonetic | PASS | APPLY | APPLY | applied Choudhury |
| case_n08_apply_bengali_surname_variant | useful_apply | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n09_apply_brand_doubled_letter | useful_apply | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n09_apply_brand_doubled_letter | useful_apply | 1 | exact | PASS | APPLY | APPLY | applied Groww |
| case_n09_apply_brand_doubled_letter | useful_apply | 1 | phonetic | PASS | APPLY | APPLY | applied Groww |
| case_n09_apply_brand_doubled_letter | useful_apply | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n10_apply_brand_dropped_vowel_zeroshot | phonetic_only | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n10_apply_brand_dropped_vowel_zeroshot | phonetic_only | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n10_apply_brand_dropped_vowel_zeroshot | phonetic_only | 1 | phonetic | PASS | APPLY | APPLY | applied Lyft |
| case_n10_apply_brand_dropped_vowel_zeroshot | phonetic_only | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n11_apply_brand_flickr_zeroshot | phonetic_only | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n11_apply_brand_flickr_zeroshot | phonetic_only | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n11_apply_brand_flickr_zeroshot | phonetic_only | 1 | phonetic | PASS | APPLY | APPLY | applied Flickr |
| case_n11_apply_brand_flickr_zeroshot | phonetic_only | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n12_apply_stylized_letters_differ | useful_apply | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n12_apply_stylized_letters_differ | useful_apply | 1 | exact | PASS | APPLY | APPLY | applied arXiv |
| case_n12_apply_stylized_letters_differ | useful_apply | 1 | phonetic | PASS | APPLY | APPLY | applied arXiv |
| case_n12_apply_stylized_letters_differ | useful_apply | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n13_apply_internal_codename | useful_apply | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n13_apply_internal_codename | useful_apply | 1 | exact | PASS | APPLY | APPLY | applied Chitragupt |
| case_n13_apply_internal_codename | useful_apply | 1 | phonetic | PASS | APPLY | APPLY | applied Chitragupt |
| case_n13_apply_internal_codename | useful_apply | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n14_phonetic_blind_ksh_x | phonetic_blind | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n14_phonetic_blind_ksh_x | phonetic_blind | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n14_phonetic_blind_ksh_x | phonetic_blind | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n14_phonetic_blind_ksh_x | phonetic_blind | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n15_phonetic_blind_initial_aa | phonetic_blind | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n15_phonetic_blind_initial_aa | phonetic_blind | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n15_phonetic_blind_initial_aa | phonetic_blind | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n15_phonetic_blind_initial_aa | phonetic_blind | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n16_phonetic_blind_dental_th | phonetic_blind | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n16_phonetic_blind_dental_th | phonetic_blind | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n16_phonetic_blind_dental_th | phonetic_blind | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n16_phonetic_blind_dental_th | phonetic_blind | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n17_phonetic_short_token_floor | phonetic_guard | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n17_phonetic_short_token_floor | phonetic_guard | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n17_phonetic_short_token_floor | phonetic_guard | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n17_phonetic_short_token_floor | phonetic_guard | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n18_formatter_regressed_name | formatter_error | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n18_formatter_regressed_name | formatter_error | 1 | exact | PASS | APPLY | APPLY | applied Sreenivas |
| case_n18_formatter_regressed_name | formatter_error | 1 | phonetic | PASS | APPLY | APPLY | applied Sreenivas |
| case_n18_formatter_regressed_name | formatter_error | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n19_formatter_regressed_brand | formatter_error | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n19_formatter_regressed_brand | formatter_error | 1 | exact | PASS | APPLY | APPLY | applied Fiverr |
| case_n19_formatter_regressed_brand | formatter_error | 1 | phonetic | PASS | APPLY | APPLY | applied Fiverr |
| case_n19_formatter_regressed_brand | formatter_error | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n20_formatter_regressed_western_name | formatter_error | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n20_formatter_regressed_western_name | formatter_error | 1 | exact | PASS | APPLY | APPLY | applied Sofia |
| case_n20_formatter_regressed_western_name | formatter_error | 1 | phonetic | PASS | APPLY | APPLY | applied Sofia |
| case_n20_formatter_regressed_western_name | formatter_error | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n21_align_contraction_expansion | alignment_stress | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n21_align_contraction_expansion | alignment_stress | 1 | exact | PASS | APPLY | APPLY | applied Karthick |
| case_n21_align_contraction_expansion | alignment_stress | 1 | phonetic | PASS | APPLY | APPLY | applied Karthick |
| case_n21_align_contraction_expansion | alignment_stress | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n22_align_hinglish_filler_stripped | alignment_stress | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n22_align_hinglish_filler_stripped | alignment_stress | 1 | exact | PASS | APPLY | APPLY | applied Priyaa |
| case_n22_align_hinglish_filler_stripped | alignment_stress | 1 | phonetic | PASS | APPLY | APPLY | applied Priyaa |
| case_n22_align_hinglish_filler_stripped | alignment_stress | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n23_align_asr_stutter | alignment_stress | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n23_align_asr_stutter | alignment_stress | 1 | exact | PASS | APPLY | APPLY | applied Deeksha |
| case_n23_align_asr_stutter | alignment_stress | 1 | phonetic | PASS | APPLY | APPLY | applied Deeksha |
| case_n23_align_asr_stutter | alignment_stress | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n24_punct_possessive | punctuation | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n24_punct_possessive | punctuation | 1 | exact | PASS | APPLY | APPLY | applied Priyaa |
| case_n24_punct_possessive | punctuation | 1 | phonetic | PASS | APPLY | APPLY | applied Priyaa |
| case_n24_punct_possessive | punctuation | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n25_punct_hyphen_segment | punctuation | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n25_punct_hyphen_segment | punctuation | 1 | exact | PASS | APPLY | APPLY | applied Kivi |
| case_n25_punct_hyphen_segment | punctuation | 1 | phonetic | PASS | APPLY | APPLY | applied Kivi |
| case_n25_punct_hyphen_segment | punctuation | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n26_punct_quoted_token | punctuation | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n26_punct_quoted_token | punctuation | 1 | exact | PASS | APPLY | APPLY | applied Neel |
| case_n26_punct_quoted_token | punctuation | 1 | phonetic | PASS | APPLY | APPLY | applied Neel |
| case_n26_punct_quoted_token | punctuation | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n27_multi_mention_per_token | multi_mention | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n27_multi_mention_per_token | multi_mention | 1 | exact | PASS | APPLY | APPLY | applied Pooja |
| case_n27_multi_mention_per_token | multi_mention | 1 | phonetic | PASS | APPLY | APPLY | applied Pooja |
| case_n27_multi_mention_per_token | multi_mention | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n28_two_entities_one_line | two_names | 2 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n28_two_entities_one_line | two_names | 2 | exact | PASS | APPLY | APPLY | applied Groww, Sreenivas |
| case_n28_two_entities_one_line | two_names | 2 | phonetic | PASS | APPLY | APPLY | applied Groww, Sreenivas |
| case_n28_two_entities_one_line | two_names | 2 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n29_refuse_conflict_two_people | conflict | 2 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n29_refuse_conflict_two_people | conflict | 2 | exact | PASS | ABSTAIN | ABSTAIN | conflicting_canonicals, no_memory |
| case_n29_refuse_conflict_two_people | conflict | 2 | phonetic | PASS | ABSTAIN | ABSTAIN | conflicting_canonicals, no_memory |
| case_n29_refuse_conflict_two_people | conflict | 2 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n30_refuse_homograph_household | context_cues | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n30_refuse_homograph_household | context_cues | 1 | exact | PASS | ABSTAIN | ABSTAIN | context_mismatch, no_memory |
| case_n30_refuse_homograph_household | context_cues | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | context_mismatch, no_memory |
| case_n30_refuse_homograph_household | context_cues | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n31_apply_homograph_work_line | context_cues | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n31_apply_homograph_work_line | context_cues | 1 | exact | PASS | APPLY | APPLY | applied Tumblr |
| case_n31_apply_homograph_work_line | context_cues | 1 | phonetic | PASS | APPLY | APPLY | applied Tumblr |
| case_n31_apply_homograph_work_line | context_cues | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n32_refuse_dictionary_add_has_no_cues | context_cues | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n32_refuse_dictionary_add_has_no_cues | context_cues | 1 | exact | PASS | APPLY | APPLY | applied Groww |
| case_n32_refuse_dictionary_add_has_no_cues | context_cues | 1 | phonetic | PASS | APPLY | APPLY | applied Groww |
| case_n32_refuse_dictionary_add_has_no_cues | context_cues | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n33_refuse_already_canonical | casing | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n33_refuse_already_canonical | casing | 1 | exact | PASS | ABSTAIN | ABSTAIN | already_canonical, no_memory |
| case_n33_refuse_already_canonical | casing | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | already_canonical, no_memory |
| case_n33_refuse_already_canonical | casing | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n34_refuse_case_only_sentence_initial | casing | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n34_refuse_case_only_sentence_initial | casing | 1 | exact | PASS | ABSTAIN | ABSTAIN | already_canonical, no_memory |
| case_n34_refuse_case_only_sentence_initial | casing | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | already_canonical, no_memory |
| case_n34_refuse_case_only_sentence_initial | casing | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n35_tolerate_hallucinated_tail | edge_robustness | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n35_tolerate_hallucinated_tail | edge_robustness | 1 | exact | PASS | APPLY | APPLY | applied Karthick |
| case_n35_tolerate_hallucinated_tail | edge_robustness | 1 | phonetic | PASS | APPLY | APPLY | applied Karthick |
| case_n35_tolerate_hallucinated_tail | edge_robustness | 1 | llm | SKIPPED | APPLY | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n36_refuse_deleted_target | edge_robustness | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n36_refuse_deleted_target | edge_robustness | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n36_refuse_deleted_target | edge_robustness | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n36_refuse_deleted_target | edge_robustness | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n37_refuse_onset_clipped | edge_robustness | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n37_refuse_onset_clipped | edge_robustness | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n37_refuse_onset_clipped | edge_robustness | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n37_refuse_onset_clipped | edge_robustness | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n38_refuse_script_switch | code_switch | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n38_refuse_script_switch | code_switch | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n38_refuse_script_switch | code_switch | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n38_refuse_script_switch | code_switch | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n39_refuse_multitoken_compound | out_of_scope | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n39_refuse_multitoken_compound | out_of_scope | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n39_refuse_multitoken_compound | out_of_scope | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n39_refuse_multitoken_compound | out_of_scope | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n40_refuse_spelled_letters | out_of_scope | 1 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n40_refuse_spelled_letters | out_of_scope | 1 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n40_refuse_spelled_letters | out_of_scope | 1 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n40_refuse_spelled_letters | out_of_scope | 1 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n41_learner_refuse_content_edit | learner_gate | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n41_learner_refuse_content_edit | learner_gate | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n41_learner_refuse_content_edit | learner_gate | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n41_learner_refuse_content_edit | learner_gate | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n42_learner_refuse_grammar_homophone | learner_gate | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n42_learner_refuse_grammar_homophone | learner_gate | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n42_learner_refuse_grammar_homophone | learner_gate | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n42_learner_refuse_grammar_homophone | learner_gate | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n43_noop_clinic_line_empty_store | noop | 0 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n43_noop_clinic_line_empty_store | noop | 0 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n43_noop_clinic_line_empty_store | noop | 0 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n43_noop_clinic_line_empty_store | noop | 0 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |
| case_n44_noop_irrelevant_store_dispatch_line | noop | 2 | off | PASS | ABSTAIN | ABSTAIN | memory disabled |
| case_n44_noop_irrelevant_store_dispatch_line | noop | 2 | exact | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n44_noop_irrelevant_store_dispatch_line | noop | 2 | phonetic | PASS | ABSTAIN | ABSTAIN | no_memory |
| case_n44_noop_irrelevant_store_dispatch_line | noop | 2 | llm | SKIPPED | ABSTAIN | None | no KIVI_LLM_API_KEY / llm producer not wired up yet |

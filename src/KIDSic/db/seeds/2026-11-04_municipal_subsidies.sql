-- Reviewed snapshot of official municipal rules on 2026-11-04.
-- Apply after Alembic upgrade head and after the three municipalities exist.
-- Monetary *_cents values are integer EUR cents, per child per month.
-- One transaction; replay updates this snapshot only and preserves its row IDs.
BEGIN;
WITH policies AS (
 SELECT value AS p FROM jsonb_array_elements($subsidy_snapshot$
[
  {
    "policy_key": "varazdin-municipal-20261104",
    "municipality_key": "varazdin",
    "provider_kinds": [
      "municipal"
    ],
    "title": "Varaždin – gradski vrtić",
    "summary": "Roditelj plaća 90, 50 ili 25 €; razliku do 450 € pokriva Grad prema obiteljskim okolnostima.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": "2026-01-01",
    "valid_until": "2028-12-31",
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "economic_price_less_parent_fee",
      "economic_price_cents": 45000,
      "rates": [
        {
          "condition": "first_child",
          "city_subsidy_cents": 36000,
          "parent_fee_cents": 9000
        },
        {
          "condition": "second_child_when_two_enrolled",
          "city_subsidy_cents": 40000,
          "parent_fee_cents": 5000
        },
        {
          "condition": "single_parent_or_disabled_homeland_war_parent",
          "city_subsidy_cents": 40000,
          "parent_fee_cents": 5000
        },
        {
          "condition": "child_with_disability_and_official_assessment",
          "city_subsidy_cents": 42500,
          "parent_fee_cents": 2500
        },
        {
          "condition": "three_or_more_simultaneously_enrolled_first_child",
          "city_subsidy_cents": 36000,
          "parent_fee_cents": 9000
        },
        {
          "condition": "three_or_more_simultaneously_enrolled_each_subsequent_child",
          "city_subsidy_cents": 42500,
          "parent_fee_cents": 2500
        }
      ],
      "eligibility": [
        "Prebivalište djeteta u Varaždinu.",
        "Olakšice ovise o istodobnom pohađanju i dokazima o statusu."
      ]
    },
    "sources": [
      {
        "url": "https://glasila.hr/upload_data/site_files/svgv1025.pdf",
        "publisher": "Grad Varaždin",
        "title": "Program javnih potreba u obrazovanju i znanosti 2026.–2028., SVGV 10/25",
        "locator": "str. 1399 i 1403; aktivnosti 53001, 53004 i 53002"
      }
    ]
  },
  {
    "policy_key": "varazdin-private-20261104",
    "municipality_key": "varazdin",
    "provider_kinds": [
      "private",
      "religious"
    ],
    "title": "Varaždin – privatni i vjerski vrtići",
    "summary": "Gradski udio iznosi 360, 400 ili 425 €; roditelj podmiruje ostatak cijene ustanove.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": "2026-01-01",
    "valid_until": "2028-12-31",
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "fixed_subsidy",
      "economic_price_reference_cap_cents": 45000,
      "rates": [
        {
          "condition": "first_child",
          "city_subsidy_cents": 36000
        },
        {
          "condition": "second_child_when_two_enrolled",
          "city_subsidy_cents": 40000
        },
        {
          "condition": "single_parent_or_disabled_homeland_war_parent",
          "city_subsidy_cents": 40000
        },
        {
          "condition": "child_with_disability_and_official_assessment",
          "city_subsidy_cents": 42500
        },
        {
          "condition": "three_or_more_simultaneously_enrolled_first_child",
          "city_subsidy_cents": 36000
        },
        {
          "condition": "three_or_more_simultaneously_enrolled_each_subsequent_child",
          "city_subsidy_cents": 42500
        }
      ],
      "eligibility": [
        "Prebivalište djeteta u Varaždinu.",
        "Redoviti program ustanove obuhvaćene gradskim sufinanciranjem."
      ],
      "parent_fee_rule": "provider_price_less_subsidy",
      "provider_participation_must_be_confirmed": true
    },
    "sources": [
      {
        "url": "https://glasila.hr/upload_data/site_files/svgv1025.pdf",
        "publisher": "Grad Varaždin",
        "title": "Program javnih potreba u obrazovanju i znanosti 2026.–2028., SVGV 10/25",
        "locator": "str. 1399 i 1403; aktivnosti 53001, 53004 i 53002"
      }
    ]
  },
  {
    "policy_key": "varazdin-childminder-20261104",
    "municipality_key": "varazdin",
    "provider_kinds": [
      "childminder"
    ],
    "title": "Varaždin – obrti dadilja",
    "summary": "Sufinanciranje postoji; aktualni iznos iz posebnog zaključka nije potvrđen.",
    "verification_status": "partial",
    "verified_on": "2026-11-04",
    "valid_from": "2026-01-01",
    "valid_until": "2028-12-31",
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "amount_unverified",
      "city_subsidy_cents": null,
      "eligibility": [
        "Prebivalište djeteta u Varaždinu.",
        "Ugovor Grada s registriranim obrtom."
      ],
      "missing_information": [
        "Aktualni zaključak koji određuje mjesečni iznos po djetetu."
      ],
      "notes": [
        "Program povezuje usklađivanje s privatnim vrtićima, ali ne potvrđuje isti cjenik."
      ]
    },
    "sources": [
      {
        "url": "https://glasila.hr/upload_data/site_files/svgv1025.pdf",
        "publisher": "Grad Varaždin",
        "title": "Program javnih potreba u obrazovanju i znanosti 2026.–2028., SVGV 10/25",
        "locator": "str. 1399 i 1403; aktivnosti 53001, 53004 i 53002"
      },
      {
        "url": "https://glasila.hr/upload_data/site_files/svgv924.pdf",
        "publisher": "Grad Varaždin",
        "title": "Izmjene Odluke o sufinanciranju djelatnosti dadilje, SVGV 9/24",
        "locator": "str. 1344–1345, akt 222, članak 1."
      }
    ]
  },
  {
    "policy_key": "zagreb-private-20261104",
    "municipality_key": "zagreb",
    "provider_kinds": [
      "private",
      "religious"
    ],
    "title": "Zagreb – privatni i vjerski vrtići",
    "summary": "Grad sufinancira 352,54–412,26 € mjesečno, ovisno o dohotku po članu kućanstva.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": "2026-01-01",
    "valid_until": "2026-12-31",
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "income_tiered_subsidy",
      "program_hours_per_day": 10,
      "program_days_per_week": 5,
      "income_basis": {
        "measure": "average_monthly_household_income_per_member",
        "reference_period": "previous_calendar_year",
        "housing_deductions": "Do 12 plaćenih rata stambenog kredita ili najamnina za stanovanje obitelji.",
        "rounding": "Pragovi su izraženi u eurocentima; postupak utvrđivanja cenzusa provodi ustanova."
      },
      "rates": [
        {
          "income_bracket": 1,
          "income_per_member": {
            "min_inclusive_cents": 104001,
            "max_inclusive_cents": null
          },
          "base_city_subsidy_cents": 17254,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 35254
        },
        {
          "income_bracket": 2,
          "income_per_member": {
            "min_inclusive_cents": 80001,
            "max_inclusive_cents": 104000
          },
          "base_city_subsidy_cents": 19245,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 37245
        },
        {
          "income_bracket": 3,
          "income_per_member": {
            "min_inclusive_cents": 58001,
            "max_inclusive_cents": 80000
          },
          "base_city_subsidy_cents": 21236,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 39236
        },
        {
          "income_bracket": 4,
          "income_per_member": {
            "min_inclusive_cents": null,
            "max_inclusive_cents": 58000
          },
          "base_city_subsidy_cents": 23226,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 41226
        }
      ],
      "eligibility": [
        "Upis u odobreni redoviti program kod sufinanciranog pružatelja u Zagrebu.",
        "Prebivalište djeteta u Zagrebu; za strane državljane propisano boravište.",
        "Odobren zahtjev; pravo od mjeseca predaje, bez retroaktivnog financiranja prethodnih mjeseci."
      ],
      "missing_income_proof_bracket": 1,
      "parent_fee_rule": "provider_price_less_subsidy",
      "sibling_relief": "Ovisi o pravilima pružatelja; nema potvrđene jedinstvene dodatne gradske olakšice.",
      "notes": [
        "Fiksnih 180 € već je uključeno u ukupni gradski iznos.",
        "Državna sredstva za fiskalnu održivost vrtića nisu gradska subvencija i ne pribrajaju se ovoj tablici."
      ]
    },
    "sources": [
      {
        "url": "https://vrtici.zagreb.hr/privatni-i-vjerski-vrtici-i-obrti-dadilja/116",
        "publisher": "Grad Zagreb",
        "title": "Sufinanciranje privatnih i vjerskih vrtića i obrta dadilja",
        "locator": "Cenzusni razredi i uvjeti"
      },
      {
        "url": "https://vrtici.zagreb.hr/UserDocsImages/Sufinanciranje/Obavijest_privatni%20i%20vjerski.pdf",
        "publisher": "Grad Zagreb",
        "title": "Službena obavijest o sufinanciranju od 1. siječnja 2026.",
        "locator": "str. 1–3"
      }
    ]
  },
  {
    "policy_key": "zagreb-childminder-20261104",
    "municipality_key": "zagreb",
    "provider_kinds": [
      "childminder"
    ],
    "title": "Zagreb – dadilje",
    "summary": "Grad sufinancira 352,54–412,26 € mjesečno, ovisno o dohotku po članu kućanstva.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": "2026-01-01",
    "valid_until": "2026-12-31",
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "income_tiered_subsidy",
      "program_hours_per_day": 8,
      "program_days_per_week": 5,
      "income_basis": {
        "measure": "average_monthly_household_income_per_member",
        "reference_period": "previous_calendar_year",
        "housing_deductions": "Do 12 plaćenih rata stambenog kredita ili najamnina za stanovanje obitelji.",
        "rounding": "Pragovi su izraženi u eurocentima; postupak utvrđivanja cenzusa provodi ustanova."
      },
      "rates": [
        {
          "income_bracket": 1,
          "income_per_member": {
            "min_inclusive_cents": 104001,
            "max_inclusive_cents": null
          },
          "base_city_subsidy_cents": 17254,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 35254
        },
        {
          "income_bracket": 2,
          "income_per_member": {
            "min_inclusive_cents": 80001,
            "max_inclusive_cents": 104000
          },
          "base_city_subsidy_cents": 19245,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 37245
        },
        {
          "income_bracket": 3,
          "income_per_member": {
            "min_inclusive_cents": 58001,
            "max_inclusive_cents": 80000
          },
          "base_city_subsidy_cents": 21236,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 39236
        },
        {
          "income_bracket": 4,
          "income_per_member": {
            "min_inclusive_cents": null,
            "max_inclusive_cents": 58000
          },
          "base_city_subsidy_cents": 23226,
          "fixed_city_top_up_cents": 18000,
          "city_subsidy_cents": 41226
        }
      ],
      "eligibility": [
        "Upis u odobreni redoviti program kod sufinanciranog pružatelja u Zagrebu.",
        "Prebivalište djeteta u Zagrebu; za strane državljane propisano boravište.",
        "Odobren zahtjev; pravo od mjeseca predaje, bez retroaktivnog financiranja prethodnih mjeseci."
      ],
      "missing_income_proof_bracket": 1,
      "parent_fee_rule": "provider_price_less_subsidy",
      "sibling_relief": "Ovisi o pravilima pružatelja; nema potvrđene jedinstvene dodatne gradske olakšice.",
      "notes": [
        "Fiksnih 180 € već je uključeno u ukupni gradski iznos.",
        "Državna sredstva za fiskalnu održivost vrtića nisu gradska subvencija i ne pribrajaju se ovoj tablici."
      ]
    },
    "sources": [
      {
        "url": "https://vrtici.zagreb.hr/privatni-i-vjerski-vrtici-i-obrti-dadilja/116",
        "publisher": "Grad Zagreb",
        "title": "Sufinanciranje privatnih i vjerskih vrtića i obrta dadilja",
        "locator": "Cenzusni razredi i uvjeti"
      },
      {
        "url": "https://vrtici.zagreb.hr/UserDocsImages/Sufinanciranje/Obavijest_dadilje.pdf",
        "publisher": "Grad Zagreb",
        "title": "Službena obavijest o sufinanciranju od 1. siječnja 2026.",
        "locator": "str. 1–3"
      }
    ]
  },
  {
    "policy_key": "zagreb-municipal-20261104",
    "municipality_key": "zagreb",
    "provider_kinds": [
      "municipal"
    ],
    "title": "Zagreb – gradski vrtići",
    "summary": "Roditeljska cijena redovitog cjelodnevnog programa iznosi 19,91–79,63 €, uz moguće olakšice.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": "2026-01-01",
    "valid_until": "2026-12-31",
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "income_tiered_parent_fee",
      "city_subsidy_cents": null,
      "income_basis": {
        "measure": "average_monthly_household_income_per_member",
        "reference_period": "previous_calendar_year",
        "housing_deductions": "Do 12 plaćenih rata stambenog kredita ili najamnina za stanovanje obitelji.",
        "rounding": "Pragovi su izraženi u eurocentima; postupak utvrđivanja cenzusa provodi ustanova."
      },
      "rates": [
        {
          "income_bracket": 1,
          "income_per_member": {
            "min_inclusive_cents": 104001,
            "max_inclusive_cents": null
          },
          "parent_fee_full_day_cents": 7963,
          "parent_fee_half_day_cents": 5176
        },
        {
          "income_bracket": 2,
          "income_per_member": {
            "min_inclusive_cents": 80001,
            "max_inclusive_cents": 104000
          },
          "parent_fee_full_day_cents": 5973,
          "parent_fee_half_day_cents": 3882
        },
        {
          "income_bracket": 3,
          "income_per_member": {
            "min_inclusive_cents": 58001,
            "max_inclusive_cents": 80000
          },
          "parent_fee_full_day_cents": 3982,
          "parent_fee_half_day_cents": 2588
        },
        {
          "income_bracket": 4,
          "income_per_member": {
            "min_inclusive_cents": null,
            "max_inclusive_cents": 58000
          },
          "parent_fee_full_day_cents": 1991,
          "parent_fee_half_day_cents": 1294
        }
      ],
      "program_hours": {
        "full_day_min": 7,
        "full_day_max": 10,
        "half_day_min": 4,
        "half_day_max": 6
      },
      "fee_without_approved_application_cents": {
        "full_day": 25217,
        "half_day": 17254
      },
      "eligibility": [
        "Upis u odobreni redoviti program kod sufinanciranog pružatelja u Zagrebu.",
        "Prebivalište djeteta u Zagrebu; za strane državljane propisano boravište.",
        "Odobren zahtjev; pravo od mjeseca predaje, bez retroaktivnog financiranja prethodnih mjeseci."
      ],
      "relief_combination": "only_most_favourable",
      "reliefs": [
        {
          "condition": "second_simultaneously_enrolled_child",
          "parent_fee_percent": 75
        },
        {
          "condition": "third_or_subsequent_simultaneously_enrolled_child",
          "parent_fee_percent": 0
        },
        {
          "condition": "single_parent",
          "parent_fee_percent": 50
        },
        {
          "condition": "special_needs_child_attending_up_to_three_hours",
          "parent_fee_percent": 40
        },
        {
          "condition": "parent_in_disability_register",
          "parent_fee_percent": 0
        },
        {
          "condition": "guaranteed_minimum_benefit",
          "parent_fee_percent": 0
        },
        {
          "condition": "temporary_foster_or_social_care_placement",
          "parent_fee_percent": 0
        },
        {
          "condition": "temporary_crisis_placement",
          "parent_fee_percent": 0
        }
      ],
      "sibling_order": "Olakšice se dodjeljuju starijoj djeci; najmlađe plaća osnovni iznos.",
      "notes": [
        "Objavljena cijena bez zahtjeva nije ovdje poistovjećena s ukupnim troškom rada vrtića.",
        "Nije potvrđena jedinstvena mjesečna gradska uplata po djetetu; pohranjene su roditeljske tarife."
      ]
    },
    "sources": [
      {
        "url": "https://vrtici.zagreb.hr/gradski-vrtici/115",
        "publisher": "Grad Zagreb",
        "title": "Sufinanciranje gradskih vrtića",
        "locator": "Cenzusni razredi, olakšice i rok zahtjeva"
      },
      {
        "url": "https://vrtici.zagreb.hr/UserDocsImages/Sufinanciranje/Obavijest_gradski.pdf",
        "publisher": "Grad Zagreb",
        "title": "Službena obavijest za gradske vrtiće od 1. siječnja 2026.",
        "locator": "str. 1–3"
      }
    ]
  },
  {
    "policy_key": "rijeka-private-20261104",
    "municipality_key": "rijeka",
    "provider_kinds": [
      "private",
      "religious"
    ],
    "title": "Rijeka – vrtići drugih osnivača",
    "summary": "Gradski udio: 335 € za jaslički, odnosno 275 € za vrtićki cjelodnevni program.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": "2026-09-01",
    "valid_until": "2027-08-31",
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "fixed_subsidy",
      "rates": [
        {
          "program": "full_day_nursery",
          "city_subsidy_cents": 33500
        },
        {
          "program": "full_day_kindergarten",
          "city_subsidy_cents": 27500
        }
      ],
      "eligibility": [
        "Ustanova u gradskoj mreži, odabrana javnim pozivom i ugovorena.",
        "Prebivalište djeteta i roditelja u Rijeci, uz iznimke za jednoroditeljske obitelji, skrb, udomiteljstvo i propisane statuse stranaca."
      ],
      "provider_participation_must_be_confirmed": true,
      "parent_fee_rule": "provider_price_less_subsidy",
      "social_relief": "Zasebna prava prema gradskoj odluci o socijalnoj skrbi; potreban individualni postupak.",
      "notes": [
        "Dodatni programi mogu imati dodatnu naplatu.",
        "Za ustanove izvan Rijeke vrijede druga pravila; ove stope odnose se na ustanove u Rijeci."
      ]
    },
    "sources": [
      {
        "url": "https://sn.rijeka.hr/2026/07/program-javnih-potreba-u-predskolskom-odgoju-i-obrazovanju-te-skrbi-o-djeci-rane-i-predskolske-dobi-grada-rijeke-za-pedagosku-godinu-2026-2027/",
        "publisher": "Grad Rijeka",
        "title": "Program javnih potreba 2026./2027., SN 11/26",
        "locator": "članci 6., 10.–13."
      }
    ]
  },
  {
    "policy_key": "rijeka-municipal-20261104",
    "municipality_key": "rijeka",
    "provider_kinds": [
      "municipal"
    ],
    "title": "Rijeka – gradski vrtići",
    "summary": "Roditelj plaća 48, 54 ili 70 € za cjelodnevni program, prema dohotku; postoje olakšice.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": null,
    "valid_until": null,
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "income_tiered_parent_fee",
      "city_subsidy_cents": null,
      "income_basis": {
        "measure": "monthly_household_income_per_member",
        "threshold_reference": "Prosječna mjesečna neto plaća RH za cijelu prethodnu godinu, prema DZS-u.",
        "threshold_eur_cents": null
      },
      "rates": [
        {
          "income_condition": "do jedne trećine prosječne plaće",
          "parent_fee_full_day_cents": 4800,
          "parent_fee_separate_half_day_group_cents": 2600,
          "parent_fee_half_day_in_full_day_group_cents": 4800
        },
        {
          "income_condition": "od jedne trećine do jedne polovine prosječne plaće",
          "parent_fee_full_day_cents": 5400,
          "parent_fee_separate_half_day_group_cents": 3000,
          "parent_fee_half_day_in_full_day_group_cents": 5400
        },
        {
          "income_condition": "više od jedne polovine prosječne plaće",
          "parent_fee_full_day_cents": 7000,
          "parent_fee_separate_half_day_group_cents": 4100,
          "parent_fee_half_day_in_full_day_group_cents": 7000
        }
      ],
      "eligibility": [
        "Dijete i najmanje jedan roditelj s prebivalištem u Rijeci; propisane iznimke za strance."
      ],
      "program_hours": {
        "full_day": 10,
        "half_day": 6
      },
      "missing_income_proof": "highest_parent_fee",
      "reliefs": [
        {
          "condition": "second_child_same_household_enrolled",
          "parent_fee_reduction_percent": 30
        },
        {
          "condition": "third_child_same_household_enrolled",
          "parent_fee_reduction_percent": 60
        },
        {
          "condition": "fourth_and_subsequent_child_same_household_enrolled",
          "parent_fee_reduction_percent": 100
        },
        {
          "condition": "illness_with_medical_proof",
          "daily_fee_reduction_percent": 20
        },
        {
          "condition": "paid_multi_day_external_educational_program",
          "daily_fee_reduction_percent": 50
        },
        {
          "condition": "private_absence_one_to_two_months_per_pedagogical_year",
          "fee_reduction_percent": 50
        },
        {
          "condition": "developmental_observation_up_to_three_hours_daily",
          "fee_reduction_percent": 70
        }
      ],
      "exempt_programs": [
        "program za djecu s teškoćama",
        "predškola",
        "poludnevni boravak u KBC-u"
      ],
      "notes": [
        "Socijalna prava utvrđuju se zasebno.",
        "Punu ekonomsku cijenu određuje gradonačelnik; iznos gradske subvencije nije izjednačen s roditeljskom tarifom.",
        "Granice izražene udjelom plaće zadržane su kako su propisane; nije izrađen kalkulator dohodovnih razreda."
      ]
    },
    "sources": [
      {
        "url": "https://sn.rijeka.hr/2024/02/odluka-o-mjerilima-za-naplatu-usluga-djecjih-vrtica-grada-rijeke-od-roditelja-korisnika-usluga/",
        "publisher": "Grad Rijeka",
        "title": "Odluka o naplati usluga gradskih vrtića, SN 2/24",
        "locator": "članci 4.–15."
      },
      {
        "url": "https://sn.rijeka.hr/2026/07/program-javnih-potreba-u-predskolskom-odgoju-i-obrazovanju-te-skrbi-o-djeci-rane-i-predskolske-dobi-grada-rijeke-za-pedagosku-godinu-2026-2027/",
        "publisher": "Grad Rijeka",
        "title": "Program javnih potreba 2026./2027., SN 11/26",
        "locator": "članci 6., 10.–13."
      }
    ]
  },
  {
    "policy_key": "rijeka-childminder-20261104",
    "municipality_key": "rijeka",
    "provider_kinds": [
      "childminder"
    ],
    "title": "Rijeka – obrti dadilja",
    "summary": "Važeći iznos iznosi 260 €; prijedlog povećanja na 310 € još je u savjetovanju.",
    "verification_status": "verified",
    "verified_on": "2026-11-04",
    "valid_from": null,
    "valid_until": null,
    "rules": {
      "schema_version": 1,
      "currency": "EUR",
      "amount_basis": "per_child_per_month",
      "funding_model": "fixed_subsidy",
      "rates": [
        {
          "city_subsidy_cents": 26000
        }
      ],
      "min_age_months": 6,
      "max_age_months_exclusive": 36,
      "age_exception": "Moguć nastavak do kraja pedagoške godine u kojoj dijete navršava tri godine.",
      "eligibility": [
        "Obrt registriran i djeluje u Rijeci.",
        "Prebivalište djeteta i roditelja kućanstva u Rijeci ili propisan privremeni boravak.",
        "Oba roditelja zaposlena, odnosno samohrani roditelj; redovito školovanje izjednačeno je sa zaposlenjem.",
        "Neupis zbog kapaciteta ili dobi; u pravilu potvrde najmanje dvaju vrtića iz mreže.",
        "Iznimke nakon upisa: naknadno zaposlenje oba roditelja ili završetak roditeljskog dopusta.",
        "Ne koristi se mirovanje radnog odnosa do treće godine za isto dijete."
      ],
      "citywide_child_quota": null,
      "quota_rule": "Godišnji broj djece odobrava gradonačelnik; nije broj djece u obitelji.",
      "pending_change": {
        "status": "consultation_not_adopted",
        "proposed_city_subsidy_cents": 31000,
        "consultation_ends_on": "2026-11-06",
        "valid_from": null,
        "source_url": "https://www.rijeka.hr/savjetovanje-o-izmjenama-i-dopuni-odluke-o-uvjetima-i-nacinu-sufinanciranja-djelatnosti-dadilja/"
      },
      "notes": [
        "Predloženi iznos nije uključen u važeće stope."
      ]
    },
    "sources": [
      {
        "url": "https://sn.rijeka.hr/2024/04/odluka-o-uvjetima-i-nacinu-financiranja-djelatnosti-dadilja/",
        "publisher": "Grad Rijeka",
        "title": "Odluka o sufinanciranju djelatnosti dadilja, SN 8/24",
        "locator": "članci 3.–8."
      },
      {
        "url": "https://www.rijeka.hr/savjetovanje-o-izmjenama-i-dopuni-odluke-o-uvjetima-i-nacinu-sufinanciranja-djelatnosti-dadilja/",
        "publisher": "Grad Rijeka",
        "title": "Savjetovanje o izmjenama odluke, 8. listopada 2026.",
        "locator": "Važećih 260 € i prijedlog 310 €; savjetovanje do 6. studenoga 2026."
      }
    ]
  }
]
$subsidy_snapshot$::jsonb)
)
INSERT INTO pravila_sufinanciranja (
 policy_key,municipality_id,provider_kinds,title,summary,verification_status,
 verified_on,valid_from,valid_until,rules,sources
)
SELECT p->>'policy_key',
 (SELECT id FROM jedinice_lokalne_samouprave WHERE key=p->>'municipality_key'),
 ARRAY(SELECT jsonb_array_elements_text(p->'provider_kinds')),
 p->>'title',p->>'summary',p->>'verification_status',
 (p->>'verified_on')::date,(p->>'valid_from')::date,(p->>'valid_until')::date,
 p->'rules',p->'sources'
FROM policies
ON CONFLICT (policy_key) DO UPDATE SET
 municipality_id=EXCLUDED.municipality_id,provider_kinds=EXCLUDED.provider_kinds,
 title=EXCLUDED.title,summary=EXCLUDED.summary,
 verification_status=EXCLUDED.verification_status,verified_on=EXCLUDED.verified_on,
 valid_from=EXCLUDED.valid_from,valid_until=EXCLUDED.valid_until,
 rules=EXCLUDED.rules,sources=EXCLUDED.sources;
COMMIT;

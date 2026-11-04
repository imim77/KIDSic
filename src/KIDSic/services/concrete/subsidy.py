"""SubsidyPolicyPresenter translates curated rules into readable rate evidence."""
from KIDSic.dto.subsidy import SubsidyPolicy, SubsidyRate


class SubsidyPolicyPresenter:
    _conditions = {
        'first_child': 'Prvo dijete',
        'second_child_when_two_enrolled': 'Drugo dijete, kada je dvoje istodobno upisano',
        'single_parent_or_disabled_homeland_war_parent': 'Samohrani roditelj ili roditelj invalid Domovinskog rata',
        'child_with_disability_and_official_assessment': 'Dijete s teškoćama i službenim nalazom',
        'three_or_more_simultaneously_enrolled_first_child': 'Troje ili više istodobno upisanih: prvo dijete',
        'three_or_more_simultaneously_enrolled_each_subsequent_child': 'Troje ili više istodobno upisanih: svako sljedeće dijete',
        'second_simultaneously_enrolled_child': 'Drugo istodobno upisano dijete',
        'third_or_subsequent_simultaneously_enrolled_child': 'Treće i svako sljedeće istodobno upisano dijete',
        'single_parent': 'Samohrani roditelj',
        'special_needs_child_attending_up_to_three_hours': 'Dijete s posebnim potrebama, boravak do tri sata',
        'parent_in_disability_register': 'Roditelj upisan u Registar osoba s invaliditetom',
        'guaranteed_minimum_benefit': 'Korisnici zajamčene minimalne naknade',
        'temporary_foster_or_social_care_placement': 'Privremeni smještaj u udomiteljstvu ili socijalnoj skrbi',
        'temporary_crisis_placement': 'Privremeni smještaj u kriznim situacijama',
        'second_child_same_household_enrolled': 'Drugo upisano dijete istog kućanstva',
        'third_child_same_household_enrolled': 'Treće upisano dijete istog kućanstva',
        'fourth_and_subsequent_child_same_household_enrolled': 'Četvrto i svako sljedeće upisano dijete istog kućanstva',
        'illness_with_medical_proof': 'Bolest uz liječničku potvrdu',
        'paid_multi_day_external_educational_program': 'Dodatno plaćeni višednevni program izvan vrtića',
        'private_absence_one_to_two_months_per_pedagogical_year': 'Privatni izostanak od jednog do dva mjeseca u pedagoškoj godini',
        'developmental_observation_up_to_three_hours_daily': 'Razvojna opservacija uz boravak do tri sata',
    }

    @staticmethod
    def _euros(cents):
        return f'{cents / 100:.2f}'.replace('.', ',') + ' €'

    def present(self, policy):
        rules = policy['rules']
        rates = []
        for rate in rules.get('rates', []):
            label = self._conditions.get(rate.get('condition'), '')
            if 'income_per_member' in rate:
                bracket = rate['income_per_member']
                lower, upper = bracket['min_inclusive_cents'], bracket['max_inclusive_cents']
                label = (f'Od {self._euros(lower)}' if upper is None else
                         f'Do {self._euros(upper)}' if lower is None else
                         f'{self._euros(lower)} – {self._euros(upper)}') + ' po članu kućanstva'
            elif 'income_condition' in rate:
                label = 'Dohodak ' + rate['income_condition']
            elif 'program' in rate:
                label = {'full_day_nursery': 'Cjelodnevne jaslice',
                         'full_day_kindergarten': 'Cjelodnevni vrtić'}.get(rate['program'], 'Redoviti program')
            if 'parent_fee_full_day_cents' in rate:
                rates.append(SubsidyRate(label=f'Cjelodnevni · {label}', parent_fee_cents=rate['parent_fee_full_day_cents']))
                half = rate.get('parent_fee_half_day_cents', rate.get('parent_fee_separate_half_day_group_cents'))
                if half is not None:
                    rates.append(SubsidyRate(label=f'Poludnevni · {label}', parent_fee_cents=half))
            else:
                rates.append(SubsidyRate(label=label or 'Mjesečno po djetetu',
                    city_subsidy_cents=rate.get('city_subsidy_cents'), parent_fee_cents=rate.get('parent_fee_cents')))
        reliefs = []
        for relief in rules.get('reliefs', []):
            label = self._conditions.get(relief['condition'])
            if label is None:
                continue
            if 'parent_fee_percent' in relief:
                suffix = f"plaća se {relief['parent_fee_percent']} % roditeljske cijene"
            else:
                key = next((k for k in ('parent_fee_reduction_percent', 'daily_fee_reduction_percent',
                                       'fee_reduction_percent') if k in relief), None)
                if key is None:
                    continue
                suffix = f"umanjenje {'dnevne' if key == 'daily_fee_reduction_percent' else 'roditeljske'} cijene za {relief[key]} %"
            reliefs.append(f'{label}: {suffix}.')
        # Research-only caveats do not describe an action a parent can take.
        notes = [note for note in rules.get('notes', []) if not note.startswith((
            'Objavljena cijena bez zahtjeva nije ovdje', 'Granice izražene udjelom plaće'))]
        if rules.get('fee_without_approved_application_cents'):
            fee = rules['fee_without_approved_application_cents']
            notes.append(f"Bez odobrenog zahtjeva: {self._euros(fee['full_day'])} za cjelodnevni "
                         f"ili {self._euros(fee['half_day'])} za poludnevni program.")
        for key in ('sibling_order', 'sibling_relief', 'social_relief', 'age_exception', 'quota_rule'):
            if rules.get(key):
                notes.append(rules[key])
        if rules.get('relief_combination') == 'only_most_favourable':
            notes.append('Primjenjuje se samo jedna, najpovoljnija olakšica.')
        if rules.get('income_basis', {}).get('threshold_reference'):
            notes.append(rules['income_basis']['threshold_reference'])
            notes.append('Poludnevna tarifa vrijedi za zasebnu poludnevnu skupinu; u cjelodnevnoj skupini naplaćuje se cjelodnevna tarifa.')
        if rules.get('income_basis', {}).get('housing_deductions'):
            notes.append('Dohodak se utvrđuje za prethodnu kalendarsku godinu. ' + rules['income_basis']['housing_deductions'])
        if rules.get('pending_change'):
            notes.append('Najavljena promjena nije uključena u prikazane važeće iznose.')
        conditions = list(rules.get('eligibility', []))
        if rules.get('program_hours_per_day'):
            conditions.append(f"Program {rules['program_hours_per_day']} sati dnevno, {rules['program_days_per_week']} dana tjedno.")
        if rules.get('min_age_months') is not None:
            conditions.append(f"Dob od navršenih {rules['min_age_months']} mjeseci do "
                              f"navršenih {rules['max_age_months_exclusive']} mjeseci, uz navedenu iznimku.")
        return SubsidyPolicy(**{key: policy[key] for key in (
            'policy_key', 'title', 'summary', 'verification_status', 'verified_on',
            'valid_from', 'valid_until', 'sources')},
            amount_kind='parent_fee' if 'parent_fee' in rules['funding_model'] else 'city_subsidy',
            rates=rates, conditions=conditions, reliefs=reliefs, notes=notes)

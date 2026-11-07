"""Zagreb's published historical table layouts, one class per layout."""
import re

from KIDSic.dto.historical import HistoricalRow, HistoricalVacancy
from KIDSic.dto.source import name_key
from KIDSic.exceptions import SourceImportError
from KIDSic.services.interfaces.historical import HistoricalTableLayout


def is_total_row(values) -> bool:
    """is_total_row recognises the published total and footnote rows, which
    carry no institution name and are not records."""
    return values[0].strip() == 'UKUPNO' or values[0].lstrip().startswith('PODACI O SLOBODNIM')


def vacancy_count(value):
    if not value.strip():
        return None  # A missing value is not zero.
    if not re.fullmatch(r'\d+', value.strip()):
        raise SourceImportError('Vacancy counts must be nonnegative integers.')
    return int(value)


class ProgramTableLayout(HistoricalTableLayout):
    """ProgramTableLayout reads one facility per row with its programs."""
    _kinds = {'Gradski vrtić': 'municipal', 'Privatni vrtić': 'private', 'Vjerski vrtić': 'religious', '': 'unknown'}

    def parse(self, table):
        header = [cell.strip() for cell in table[0]]
        required = ('Name', 'Description', 'VRSTA', 'PROGRAMI')
        if any(header.count(key) != 1 for key in required):
            raise SourceImportError('Unexpected historical program columns.')
        result = []
        for values in table[1:]:
            if not any(cell.strip() for cell in values):
                continue
            if len(values) != len(header):
                raise SourceImportError('Historical program row width does not match its header.')
            raw = dict(zip(header, values))
            name, address = raw['Name'].strip(), raw['Description'].strip()
            if not name or not address:
                raise SourceImportError('Historical programs require institution name and object address.')
            kind = self._kinds.get(raw['VRSTA'].strip())
            if kind is None:
                raise SourceImportError('Unexpected historical provider type.')
            programs = tuple(dict.fromkeys(p.strip() for p in raw['PROGRAMI'].split(';')
                                          if p.strip() not in {'', '/'}))
            result.append(HistoricalRow(f'{name_key(name)}|{name_key(address)}', name,
                address, kind, 'facility', raw, programs=programs))
        return result


class MunicipalVacancyLayout(HistoricalTableLayout):
    """MunicipalVacancyLayout reads institution vacancies per age and program."""
    dated = True

    def parse(self, table):
        if len(table) < 4 or table[0][:3] != ['Gradska četvrt', 'Naziv dječjeg vrtića',
                                           'Područni objekti u drugim gradskim četvrtima']:
            raise SourceImportError('Unexpected municipal vacancy header.')
        if any(len(row) != 23 for row in table[:3]):
            raise SourceImportError('Unexpected municipal vacancy header width.')
        # Three merged header rows: totals are not additional age/program groups.
        columns, age = [], ''
        for index in range(3, len(table[0])):
            age = table[1][index].strip() or age
            program = table[2][index].strip()
            if age.startswith('od ') and program in {'REDOVITI PROGRAM', 'POSEBNI PROGRAM'}:
                columns.append((index, age, program))
        if len(columns) != 14:
            raise SourceImportError('Unexpected municipal vacancy age/program groups.')
        result = []
        for values in table[3:]:
            if not any(cell.strip() for cell in values):
                continue
            if len(values) != len(table[0]):
                raise SourceImportError('Municipal vacancy row width changed.')
            if not values[1].strip():
                if is_total_row(values):
                    continue
                raise SourceImportError('Missing municipal institution name.')
            name = values[1].strip()
            vacancies = tuple(HistoricalVacancy(age_label=age, program=program, free_places=vacancy_count(values[index]))
                for index, age, program in columns)
            result.append(HistoricalRow(name_key(name), name, None, 'municipal', 'institution',
                {'headers': table[:3], 'cells': values}, vacancies=vacancies))
        return result


class ChildminderVacancyLayout(HistoricalTableLayout):
    """ChildminderVacancyLayout reads one vacancy count per childminder."""
    dated = True

    def parse(self, table):
        header = [' '.join(cell.split()) for cell in table[0]]
        if header != ['Gradska četvrt', 'GČ', 'Naziv obrta za čuvanje djece (dadilje)',
                      'Broj slobodnih mjesta od 1 godine do OŠ']:
            raise SourceImportError('Unexpected childminder vacancy header.')
        result = []
        for values in table[1:]:
            if not any(cell.strip() for cell in values):
                continue
            if len(values) != 4:
                raise SourceImportError('Childminder vacancy row width changed.')
            if not values[2].strip():
                if is_total_row(values):
                    continue
                raise SourceImportError('Missing childminder name.')
            name, count = values[2].strip(), vacancy_count(values[3])
            vacancies = (HistoricalVacancy(age_label='od 1 godine do OŠ', free_places=count),)
            result.append(HistoricalRow(name_key(name), name, None, 'childminder', 'institution',
                dict(zip(header, values)), vacancies=vacancies))
        return result


def default_historical_layouts() -> dict[str, HistoricalTableLayout]:
    return {'programs': ProgramTableLayout(), 'municipal-vacancies': MunicipalVacancyLayout(),
            'childminder-vacancies': ChildminderVacancyLayout()}

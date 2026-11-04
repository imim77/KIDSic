"""HistoricalTableParser preserves source granularity and excludes published totals."""
import re
from collections import Counter

from KIDSic.dto.historical import HistoricalRow, HistoricalVacancy, HistoricalSourceDefinition
from KIDSic.dto.source import name_key
from KIDSic.exceptions import SourceImportError


class HistoricalTableParser:
    def parse(self, table: list[list[str]], definition: HistoricalSourceDefinition) -> tuple[HistoricalRow, ...]:
        if not table:
            raise SourceImportError('Historical table is empty.')
        parser = definition.source.parser
        if parser == 'programs':
            rows = self._programs(table)
        elif parser == 'municipal-vacancies':
            self._check_date(table, definition)
            rows = self._municipal(table)
        elif parser == 'childminder-vacancies':
            self._check_date(table, definition)
            rows = self._childminders(table)
        else:
            raise SourceImportError(f'Unknown historical parser: {parser}.')
        duplicates = [key for key, count in Counter(r.source_key for r in rows).items() if count > 1]
        if not rows or duplicates:
            raise SourceImportError('Historical table has no records or duplicate identities.')
        return tuple(rows)

    @staticmethod
    def _check_date(table, definition):
        dates = re.findall(r'STANJE NA DAN\s+(\d+)\.(\d+)\.(\d{4})\.',
                           ' '.join(cell for row in table for cell in row), re.I)
        expected = definition.reference_date
        if dates != [(str(expected.day), str(expected.month), str(expected.year))]:
            raise SourceImportError('Historical observation date does not match the configured snapshot.')

    @staticmethod
    def _count(value):
        if not value.strip():
            return None  # A missing value is not zero.
        if not re.fullmatch(r'\d+', value.strip()):
            raise SourceImportError('Vacancy counts must be nonnegative integers.')
        return int(value)

    def _programs(self, table):
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
            kind = {'Gradski vrtić': 'municipal', 'Privatni vrtić': 'private',
                    'Vjerski vrtić': 'religious', '': 'unknown'}.get(raw['VRSTA'].strip())
            if kind is None:
                raise SourceImportError('Unexpected historical provider type.')
            programs = tuple(dict.fromkeys(p.strip() for p in raw['PROGRAMI'].split(';')
                                          if p.strip() not in {'', '/'}))
            result.append(HistoricalRow(f'{name_key(name)}|{name_key(address)}', name,
                address, kind, 'facility', raw, programs=programs))
        return result

    def _municipal(self, table):
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
                if values[0].strip() == 'UKUPNO' or values[0].lstrip().startswith('PODACI O SLOBODNIM'):
                    continue
                raise SourceImportError('Missing municipal institution name.')
            name = values[1].strip()
            vacancies = tuple(HistoricalVacancy(age_label=age, program=program, free_places=self._count(values[index]))
                for index, age, program in columns)
            result.append(HistoricalRow(name_key(name), name, None, 'municipal', 'institution',
                {'headers': table[:3], 'cells': values}, vacancies=vacancies))
        return result

    def _childminders(self, table):
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
                if values[0].strip() == 'UKUPNO' or values[0].lstrip().startswith('PODACI O SLOBODNIM'):
                    continue
                raise SourceImportError('Missing childminder name.')
            name, count = values[2].strip(), self._count(values[3])
            vacancies = (HistoricalVacancy(age_label='od 1 godine do OŠ', free_places=count),)
            result.append(HistoricalRow(name_key(name), name, None, 'childminder', 'institution',
                dict(zip(header, values)), vacancies=vacancies))
        return result

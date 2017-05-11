from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pandas

from doppelganger import inputs


class Population(object):

    @staticmethod
    def from_csvs(persons_infile, households_infile):
        """Load generated population from file.

        Args:
            persons_infile (unicode): path to persons csv
            households_infile (unicode): path to households csv

        Returns:
            Population: generated population

        """
        generated_people = pandas.read_csv(persons_infile)
        generated_households = pandas.read_csv(households_infile)
        return Population(generated_people, generated_households)

    def __init__(self, generated_people, generated_households):
        self.generated_people = generated_people
        self.generated_households = generated_households

    @staticmethod
    def _extract_evidence(allocated_rows, fields, segmenter):
        """Creates a generator in the pythonic sense yielding
         (serial number, evidence, segment)
        """
        serialnos = set()
        for _, row in allocated_rows.iterrows():
            serialno = row[inputs.SERIAL_NUMBER.name]
            if serialno in serialnos:
                # Don't generate more than once for the same serial number
                continue
            serialnos.add(serialno)
            evidence = tuple((field, row[field]) for field in fields)
            segment = segmenter(row)
            yield serialno, evidence, segment

    @staticmethod
    def _generate_from_model(household_allocator, data, model, fields):
        """Generate the given fields of the given data generated by the
        given model
        """
        results = []
        for serialno, evidence, segment in Population._extract_evidence(
                data,
                fields,
                model.segmenter
        ):
            count_info = household_allocator.get_counts(serialno)
            for tract, count in count_info:
                generated_rows = model.generate(segment, evidence, count=count)
                for repeat_id, row in enumerate(generated_rows):
                    results.append((tract, serialno, repeat_id) + row)

        column_names = ['tract', inputs.SERIAL_NUMBER.name,
                        'repeat_index'] + list(model.fields)
        results_dataframe = pandas.DataFrame(results, columns=column_names)
        return results_dataframe

    @staticmethod
    def generate(household_allocator, person_model, household_model):
        """Create all the persons and households for this population

        Args:
            household_allocator (HouseholdAllocator): allocated households
            person_model (BayesianNetworkNodel): optional generative model
            household_model (BayesianNetworkNodel): optional generative model

        Returns: Population from the given model
        """

        persons = Population._generate_from_model(
            household_allocator, household_allocator.allocated_persons,
            person_model, [inputs.AGE.name, inputs.SEX.name]
        )
        households = Population._generate_from_model(
            household_allocator, household_allocator.allocated_households,
            household_model, [inputs.NUM_PEOPLE.name]
        )
        return Population(persons, households)

    def write(self, persons_outfile, households_outfile):
        """Write population to the given file

        Args:
            outfile (unicode): path to write to

        """
        self.generated_people.to_csv(persons_outfile)
        self.generated_households.to_csv(households_outfile)
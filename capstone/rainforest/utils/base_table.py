from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Type
from pathlib import Path

from pyspark.sql import DataFrame
import great_expectations as gx


@dataclass
class ETLDataSet:
    name: str
    curr_data: DataFrame
    primary_keys: List[str]
    storage_path: str
    data_format: str
    database: str
    partition_keys: List[str]


class TableETL(ABC):
    @abstractmethod
    def __init__(
        self,
        spark,
        upstream_table_names: Optional[List[Type[TableETL]]],
        name: str,
        primary_keys: List[str],
        storage_path: str,
        data_format: str,
        database: str,
        partition_keys: List[str],
        run_upstream: bool = True,
    ) -> None:
        self.spark = spark
        self.upstream_table_names = upstream_table_names
        self.name = name
        self.primary_keys = primary_keys
        self.storage_path = storage_path
        self.data_format = data_format
        self.database = database
        self.partition_keys = partition_keys
        self.run_upstream = run_upstream

    @abstractmethod
    def extract_upstream(self) -> List[ETLDataSet]:
        pass

    @abstractmethod
    def transform_upstream(
        self, upstream_datasets: List[ETLDataSet]
    ) -> ETLDataSet:
        pass

    def validate(self, data: ETLDataSet) -> bool:
        file_path = Path(f"capstone/rainforest/great_expectations/expectations/{self.name}.json")

        if file_path.exists():
            # validate
            # Perform any necessary validation checks on the transformed data
            context = gx.get_context(
                context_root_dir=os.path.join(
                    os.getcwd(),
                    "capstone",
                    "rainforest",
                    "great_expectations",
                )
            )

            validations = []
            validations.append(
                {
                    "batch_request": context.get_datasource("spark_datasource")
                    .get_asset(self.name)
                    .build_batch_request(dataframe=data.curr_data),
                    "expectation_suite_name": self.name,
                }
            )
            return context.run_checkpoint(
                checkpoint_name="dq_checkpoint", validations=validations
            ).list_validation_results()

        else:
            return True

    @abstractmethod
    def load(self, data: ETLDataSet) -> None:
        pass

    def run(self) -> None:
        transformed_data = self.transform_upstream(self.extract_upstream())
        self.validate(transformed_data)
        self.load(transformed_data)

    @abstractmethod
    def read(
        self, partition_values: Optional[Dict[str, str]] = None
    ) -> ETLDataSet:
        pass

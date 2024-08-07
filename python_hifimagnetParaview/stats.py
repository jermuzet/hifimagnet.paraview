import pandas as pd
import os

from tabulate import tabulate

from paraview.simple import (
    DescriptiveStatistics,
    Delete,
    ExportView,
    CreateView,
    Show,
)

from .method import convert_data, resultinfo, keyinfo
from .histo import getresultHisto


def createTable(file: str, key: str, name: str, verbose: bool = False):
    """create statistics table

    Args:
        file (str): csv file name
        key (str): field name
        name (str): block name
        verbose (bool, optional): print verbose. Defaults to False.

    Returns:
        _stat
    """
    csv = pd.read_csv(file)
    keys = csv.columns.values.tolist()
    if verbose:
        print(f"createTable: file={file}, key={key}", flush=True)
    # print(tabulate(csv, headers="keys", tablefmt="psql"))

    # drop following keys
    csv.rename(columns={"Block Name": "BlockName"}, inplace=True)
    dropped_keys = ["Row ID", "Cardinality", "Kurtosis", "Skewness", "Sum", "Variance"]
    csv.drop(columns=dropped_keys, inplace=True)

    # print("createTable: post-process stats table", flush=True)
    # print(tabulate(csv, headers="keys", tablefmt="psql"))

    # for each row "Derived Stats" copy value to "Primary Statistics"
    primary = csv.query("BlockName == 'Primary Statistics'").dropna(axis="columns")
    # print(tabulate(primary, headers="keys", tablefmt="psql"))
    primary.drop(columns=["BlockName"], inplace=True)
    # print("primary:", tabulate(primary, headers="keys", tablefmt="psql"))
    derived = csv.query("BlockName == 'Derived Statistics'").dropna(axis="columns")
    derived.reset_index(drop=True, inplace=True)
    # print("derived:", tabulate(derived, headers="keys", tablefmt="psql"))
    derived.drop(columns=["BlockName"], inplace=True)
    stats_ = primary.join(derived)
    # print(tabulate(stats_, headers="keys", tablefmt="psql"))

    (nrows, ncols) = stats_.shape
    stats_["Name"] = [name for i in range(nrows)]
    # print("join:\n", tabulate(stats_, headers="keys", tablefmt="psql"))
    return stats_


def createStatsTable(
    stats: list, name: str, fieldunits: dict, basedir: str, ureg, verbose: bool = False
) -> pd.DataFrame:
    """create statistic table & csv file

    Args:
        stats (list): statistics
        name (str): block name
        fieldunits (dict): dict of field ubits
        basedir (str): result directory
        ureg: pint unit registry
        verbose (bool, optional): print verbose. Defaults to False.

    Returns:
        pd.DataFrame: statistics dataframe
    """
    os.makedirs(f"{basedir}/stats", exist_ok=True)
    # TODO add a column with the Block Name
    # the column Block Name in cvs is not what I think
    # it is either "Primary Statistics" or "Derived Statistics"
    # remove "Derived Statistics" rows
    # why Standard Deviation and Variance are NaN??
    print(
        f"createStatsTable: name={name}, aggregate stats by datatype and field ({len(stats)}) items",
        flush=True,
    )
    _dataset = {
        "PointData": {},
        "CellData": {},
        "FieldData": {},
    }

    for statdict in stats:
        for datatype in statdict:
            # print(f"datatype={datatype}", flush=True)
            for key, kdata in statdict[datatype]["Arrays"].items():
                # print(f"key={key} kdata={kdata.keys()}", flush=True)
                if "Stats" in kdata:
                    if not key in _dataset[datatype]:
                        # print(f"create _dataset[{datatype}][{key}]", flush=True)
                        _dataset[datatype][key] = []

                    # print(f"append kdata[Stats] to _dataset[{datatype}][{key}]", flush=True)
                    _dataset[datatype][key].append(kdata["Stats"])

    # print("_dataset:", flush=True)
    dfs = []
    for datatype in _dataset:
        # print(f"datatype={datatype}", flush=True)
        for key in _dataset[datatype]:
            # print(f"DescriptiveStats for datatype={datatype}, key={key}:", flush=True)
            # print(f"dataset: {len(_dataset[datatype][key])}", flush=True)

            (toolbox, physic, fieldname) = keyinfo(key)
            units = {fieldname: fieldunits[fieldname]["Units"]}
            # print(f"toolxbox={toolbox}, physic={physic}, fieldname={fieldname}", flush=True)
            # print(f'fieldunits[fieldname]={fieldunits[fieldname]}"', flush=True)
            symbol = fieldunits[fieldname]["Symbol"]
            [in_unit, out_unit] = fieldunits[fieldname]["Units"]
            # print(f"in_units={in_unit}, out_units={out_unit}", flush=True)

            """
            # Exclude row with Name in fieldunits[fieldname]['Exclude']
            excludeblocks = fieldunits[fieldname]["Exclude"]
            found = False
            for block in excludeblocks:
                if block in name:
                    found = True
                    print(f"ignore block: {block}", flush=True)
                    break
            """

            # for dset in _dataset[datatype][key]:
            #     print(tabulate(dset, headers="keys", tablefmt="psql"))
            df = pd.concat(_dataset[datatype][key])
            # print(f"Aggregated DescriptiveStats for datatype={datatype}, key={key}:", flush=True)

            # Reorder columns
            df = df[
                [
                    "Variable",
                    "Name",
                    "Minimum",
                    "Mean",
                    "Maximum",
                    "Standard Deviation",
                    "M2",
                    "M3",
                    "M4",
                ]
            ]

            # how to: rewrite tab contents using symbol and units
            # see: https://github.com/pandas-dev/pandas/issues/29435
            values = df["Variable"].to_list()
            # print(f"values={values}", flush=True)
            out_values = [value.replace(key, rf"{symbol}") for value in values]
            out_values = [rf"{value} [{out_unit:~P}]" for value in out_values]
            df = df.assign(Variable=out_values)
            # print(f"df[Variable]={df['Variable'].to_list()}", flush=True)
            # print(f"out_values={out_values}", flush=True)
            ndf = {}
            for column in ["Minimum", "Mean", "Maximum", "Standard Deviation"]:
                values = df[column].to_list()
                # print(f"{column}:", flush=True)
                # print(f"values={values}", flush=True)
                if (
                    column == "Standard Deviation"
                    and units[fieldname][0] == ureg.kelvin
                ):
                    out_values = values
                else:
                    out_values = convert_data(units, values, fieldname)
                # print(f"out_values={out_values}", flush=True)
                # print(
                #     f"format out_values={[f'{val:.2f}' for val in out_values]}",
                #     flush=True,
                # )
                ndf[column] = [f"{val:.3f}" for val in out_values]
            # print(f'ndf={ndf}', flush=True)
            scaled_df = pd.DataFrame.from_dict(ndf)
            for column in ["Minimum", "Mean", "Maximum", "Standard Deviation"]:
                df[column] = scaled_df[column]
                # print(f'df[{column}]={df[column].to_list()}', flush=True)

            # watch out:
            # M2: moment of order 2 (square of mean)
            # M3: moment of order 3 (cube of mean)
            # M4: moment of order 4 (cube of mean)
            # print("change units for Moments", flush=True)
            ndf = {}
            Munits = [in_unit, out_unit]
            if in_unit == ureg.kelvin:
                Munits = [in_unit, in_unit]
            # print(f"units={units}, type={type(units)}", flush=True)
            # print(f"Munits={Munits}, type={type(Munits)}", flush=True)
            for column in ["M2", "M3", "M4"]:
                # print(f"column={column}", flush=True)
                values = df[column].to_list()
                # print(f"values={values}", flush=True)

                MomentUnits = {column: []}
                for i, unit in enumerate(Munits):
                    # print(f"i={i}", flush=True)
                    unit_ = fieldunits[fieldname]["Units"][i]
                    if fieldunits[fieldname]["Units"][0] == ureg.kelvin:
                        unit_ = ureg.kelvin
                    # print(f"units[{i}]={unit_}", flush=True)
                    # print(f"Munits[{i}]={Munits[i]}", flush=True)
                    MomentUnits[column].append(Munits[i] * unit_)
                    # print(
                    #     f"MomentUnits[{column}]={MomentUnits[column][-1]}",
                    #     flush=True,
                    # )
                    Munits[i] = Munits[i] * unit_
                # print(f"MomentUnits[{column}]={MomentUnits[column]}", flush=True)

                out_values = convert_data(MomentUnits, values, column)
                ndf[column] = [f"{val:.3f}" for val in out_values]
                del MomentUnits[column]

            scaled_df = pd.DataFrame.from_dict(ndf)
            for column in ["M2", "M3", "M4"]:
                # print(f"df[{column}]={df[column].to_list()}", flush=True)
                df[column] = scaled_df[column]
                # print(f"scaled df[{column}]={df[column].to_list()}", flush=True)

            if verbose:
                print(
                    tabulate(df, headers="keys", tablefmt="psql", showindex=False),
                    flush=True,
                )
            df.to_csv(f"{basedir}/stats/{key}-descriptivestats.csv")
            dfs.append(df)

    total_df = pd.DataFrame()
    if dfs:
        total_df = pd.concat(dfs)
        print(
            tabulate(total_df, headers="keys", tablefmt="psql", showindex=False),
            flush=True,
        )
        total_df.to_csv(f"{basedir}/stats/{name}-descriptivestats.csv")

        # remove temporary csv files
        for datatype in _dataset:
            for key in _dataset[datatype]:
                try:
                    os.remove(f"{basedir}/stats/{key}-descriptivestats.csv")
                    os.remove(f"{basedir}/stats/{name}-{key}-descriptivestats.csv")
                except:
                    pass

    return total_df


def getresultStats(
    input,
    name: str,
    key: str,
    AttributeMode: str,
    basedir: str,
    printed: bool = True,
    verbose: bool = False,
) -> str:
    """compute stats for key

    Args:
        input (_type_): paraview reader
        name (str): block name
        key (str): field name
        AttributeMode (str): "Point Data" or "Cell Data" or "Field Data"
        basedir (str): result directory
        printed (bool, optional): Defaults to True.
        verbose (bool, optional): print verbose. Defaults to False.

    Returns:
        str: csv file name
    """ """
    
    """
    os.makedirs(f"{basedir}/stats", exist_ok=True)

    if verbose:
        print(
            f"getresultStats: name={name}, key={key}, AttributeMode={AttributeMode}",
            flush=True,
        )

    # if field is a vector, create a field for its norm

    # statistics
    statistics = DescriptiveStatistics(input)
    # get params list
    if not printed:
        for prop in statistics.ListProperties():
            print(
                f"DescriptiveStatistics: {prop}={statistics.GetPropertyValue(prop)}",
                flush=True,
            )
    statistics.VariablesofInterest = [key]
    statistics.AttributeMode = AttributeMode
    # statistics.UpdatePipeline()
    # stats_info = statistics.GetDataInformation()
    # SetActiveSource(statistics)

    spreadSheetView = CreateView("SpreadSheetView")
    descriptiveStatisticsDisplay = Show(
        statistics, spreadSheetView, "SpreadSheetRepresentation"
    )
    spreadSheetView.Update()

    filename = f"{basedir}/stats/{name}-{key}-descriptivestats.csv"
    export = ExportView(
        filename,
        view=spreadSheetView,
        RealNumberNotation="Scientific",
    )

    # if not printed:
    #     # get params list
    #     for prop in export.ListProperties():
    #         print(f'ExportView: {prop}={export.GetPropertyValue(prop)}', flush=True)

    Delete(descriptiveStatisticsDisplay)
    Delete(spreadSheetView)
    del spreadSheetView
    Delete(statistics)
    del statistics

    csv = createTable(filename, key, name, verbose)

    return csv


def resultStats(
    input,
    name: str,
    dim: int,
    AreaorVolume: float,
    fieldunits: dict,
    ignored_keys: list[str],
    ureg,
    basedir: str,
    histo: bool = False,
    BinCount: int = 10,
    show: bool = False,
    verbose: bool = False,
) -> dict:
    """compute stats for PointData, CellData and FieldData

    Args:
        input: paraview reader
        name (str): block name
        dim (int): geometry dimmension
        AreaorVolume (float): total area or volume
        fieldunits (dict): dict of field units
        ignored_keys (list[str]): list of ignored fields
        ureg (_type_): pint unit registry
        basedir (str): result directory
        histo (bool, optional): compute histograms. Defaults to False.
        BinCount (int, optional): number of bins in histograms. Defaults to 10.
        show (bool, optional): show histograms. Defaults to False.
        verbose (bool, optional): print verbose. Defaults to False.

    Returns:
        dict: statistics dict
    """
    datadict = resultinfo(input, ignored_keys, verbose)
    if verbose:
        print(f"resultStats[{name}]: datadict={datadict}", flush=True)

    for datatype in datadict:
        if datatype != "FieldData":
            AttributeMode = datadict[datatype]["AttributeMode"]
            TypeMode = datadict[datatype]["TypeMode"]
            for key, kdata in datadict[datatype]["Arrays"].items():
                if not key in ignored_keys:

                    found = False
                    (toolbox, physic, fieldname) = keyinfo(key)

                    for excluded in fieldunits[fieldname]["Exclude"]:
                        if excluded in name:
                            found = True
                            if verbose:
                                print(f"ignore block: {name}", flush=True)
                            break

                    if not found:
                        Components = kdata["Components"]
                        bounds = kdata["Bounds"]
                        if bounds[0][0] != bounds[0][1]:
                            if not "Stats" in kdata:
                                # print(f"\t{key}: create kdata[Stats]", flush=True)
                                kdata["Stats"] = {}

                            kdata["Stats"] = getresultStats(
                                input,
                                name,
                                key,
                                AttributeMode,
                                basedir,
                                verbose=verbose,
                            )

                            if histo:
                                getresultHisto(
                                    input,
                                    name,
                                    dim,
                                    AreaorVolume,
                                    fieldunits,
                                    key,
                                    TypeMode,
                                    basedir,
                                    Components,
                                    BinCount=BinCount,
                                    show=show,
                                    verbose=verbose,
                                )
    # display stats
    return datadict

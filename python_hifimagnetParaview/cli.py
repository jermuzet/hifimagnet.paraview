# import vtk
import pandas as pd
import matplotlib.pyplot as plt

from typing import List

from paraview.simple import (
    ExtractBlock,
    ExtractSurface,
    GetParaViewVersion,
    Delete,
    SaveData,
)


from .method import load, info, getbounds, resultinfo
from .view import deformed, makethetaclip
from .json import returnExportFields

pd.options.mode.copy_on_write = True

import argparse, argcomplete
import os
import sys

from pint import UnitRegistry, Quantity

# Ignore warning for pint
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    Quantity([])
warnings.filterwarnings("ignore")


def options(description: str, epilog: str):
    """
    define options
    """
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    subparsers = parser.add_subparsers(
        title="dimmension", dest="dimmension", help="sub-dimmension help"
    )
    parser_3D = subparsers.add_parser("3D", help="3D model")
    parser_2D = subparsers.add_parser("2D", help="2D model")
    parser_Axi = subparsers.add_parser("Axi", help="Axi model")
    for allparsers in [parser_3D, parser_2D, parser_Axi]:
        allparsers.add_argument(
            "file", type=str, help="input case file (ex. Export.case)"
        )
        allparsers.add_argument(
            "--field", type=str, help="select field to display", default=""
        )
        allparsers.add_argument(
            "--customRangeHisto",
            help="create views custom range from histogramms",
            action="store_true",
        )
        allparsers.add_argument(
            "--stats", help="activate stats calculations", action="store_true"
        )
        allparsers.add_argument(
            "--histos", help="activate histograms calculations", action="store_true"
        )
        allparsers.add_argument(
            "--bins", type=int, help="set bins number (default 10)", default=20
        )
        allparsers.add_argument(
            "--plots", help="activate plots calculations", action="store_true"
        )
        allparsers.add_argument(
            "--plotsMarker",
            help="Choose marker for plots calculations",
            type=str,
            default="",
        )
        allparsers.add_argument(
            "--views", help="activate views calculations", action="store_true"
        )
        allparsers.add_argument(
            "--transparentBG",
            help="transparent background for views",
            action="store_true",
        )

        allparsers.add_argument(
            "--cliptheta",
            type=float,
            help="select theta in deg to display",
            default=None,
        )
        allparsers.add_argument(
            "--r", nargs="*", type=float, help="select r in m to display"
        )
        if allparsers != parser_Axi:
            allparsers.add_argument(
                "--theta", nargs="*", type=float, help="select theta in deg to display"
            )
        if allparsers != parser_2D:
            allparsers.add_argument(
                "--channels", help="activate views calculations", action="store_true"
            )
            allparsers.add_argument(
                "--z", nargs="*", type=float, help="select z in m to display"
            )
        allparsers.add_argument(
            "--greyspace",
            help="plot grey bar for holes in plot",
            action="store_true",
        )
        allparsers.add_argument(
            "--deformedfactor",
            type=int,
            help="select factor for deformed views",
            default=1,
        )
        allparsers.add_argument(
            "--save",
            help="save graphs",
            action="store_true",
        )
        allparsers.add_argument(
            "--verbose",
            help="activate verbose mode",
            action="store_true",
        )
        allparsers.add_argument(
            "--json", type=str, help="input json file for fieldunits", default=None
        )

    # TODO get Exports section from json model file
    # data['PostProcess'][method_params[0]]['Exports']['expr']?
    #
    # provides
    # * field: symbol, unit, support, ...
    # * list of operations to perform (to be implemented?)
    #

    return parser


def init(file: str):
    # get current working directory
    cwd = os.getcwd()
    print("workingdir=", cwd)

    basedir = f"{os.path.dirname(file)}/paraview.exports"
    # basedir = os.path.dirname(args.file).replace(f"{toolbox}.export", "paraview.export")
    print("Results are stored in: ", basedir, flush=True)
    os.makedirs(basedir, exist_ok=True)

    # Pint configuration
    ureg = UnitRegistry()
    ureg.define("percent = 0.01 = %")
    ureg.define("ppm = 1e-6")
    ureg.default_system = "SI"
    ureg.autoconvert_offset_to_baseunit = True

    # set default output unit to millimeter
    distance_unit = "millimeter"  # or "meter"

    # check paraview version
    version = GetParaViewVersion()
    print(f"Paraview version: {version}", flush=True)

    # args.file = "../../HL-31/test/hybride-Bh27.7T-Bb9.15T-Bs9.05T_HPfixed_BPfree/bmap/np_32/thermo-electric.exports/Export.case"
    reader = load(file)
    # print(f"help(reader) = {dir(reader)}",flush=True)
    bounds = getbounds(reader)
    print(f"bounds={bounds}", flush=True)  # , type={type(bounds)}",flush=True)
    info(reader)
    # color = None
    # CellToData = False

    return cwd, basedir, ureg, distance_unit, reader


def showplot(figaxs: dict, title: str, basedir: str, show: bool = True):
    for f in figaxs:
        print(f"plot {f}{title}", flush=True)
        axs = figaxs[f]
        axs[1].legend(axs[2], fontsize=18, loc="best")
        axs[1].set_title(f"{f}{title} ", fontsize=20)
        axs[1].grid(True, linestyle="--")
        axs[1].tick_params(axis="x", which="major", labelsize=15)
        axs[1].tick_params(axis="y", which="major", labelsize=15)
        if show:
            axs[0].show()
        else:
            axs[0].tight_layout()
            axs[0].savefig(f"{basedir}/plots/{f}{title}.png", dpi=300)


def main():

    parser = options("", "")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    print(f"args: {args}")

    match args.dimmension:
        case "3D":
            from .meshinfo import meshinfo
            from .case3D.plot import plotOr, plotTheta, plotOz
            from .case3D.display3D import makeview
            from .case3D.method3D import create_dicts, create_dicts_fromjson

            dim = 3
            axis = False
        case "2D":
            from .meshinfo import meshinfo
            from .case2D.plot import plotOr, plotTheta
            from .case2D.display2D import makeview
            from .case2D.method2D import create_dicts, create_dicts_fromjson

            dim = 2
            axis = False
        case "Axi":
            from .meshinfoAxi import meshinfo
            from .caseAxi.plot import plotOr, plotOz
            from .case2D.display2D import makeview
            from .caseAxi.methodAxi import create_dicts, create_dicts_fromjson

            dim = 2
            axis = True
        case _:
            pass

    (cwd, basedir, ureg, distance_unit, reader) = init(args.file)

    if args.json:
        fieldtype = returnExportFields(args.json, basedir)
        fieldunits, ignored_keys = create_dicts_fromjson(
            fieldtype, ureg, distance_unit, basedir
        )
    else:
        fieldunits, ignored_keys = create_dicts(ureg, distance_unit, basedir)

    if dim == 2 and args.cliptheta:
        reader = makethetaclip(reader, args.cliptheta, invert=False)

    if args.field:
        if args.field in list(reader.CellData.keys()):
            field = reader.CellData[args.field]
            # if field.GetNumberOfComponents() == 1:
            color = ["CELLS", args.field]
            # if field.GetNumberOfComponents() == dim:
            #    color = ["CELLS", args.field, "Magnitude"]
        if args.field in list(reader.PointData.keys()):
            field = reader.PointData[args.field]
            # if field.GetNumberOfComponents() == 1:
            color = ["POINTS", args.field]
            # if field.GetNumberOfComponents() == dim:
            #    color = ["POINTS", args.field, "Magnitude"]

    # get Block info
    cellsize, blockdata, statsdict = meshinfo(
        reader,
        dim,
        fieldunits,
        ignored_keys,
        basedir,
        ureg,
        ComputeStats=args.stats,
        ComputeHisto=args.histos,
        BinCount=args.bins,
        show=(not args.save),
        verbose=args.verbose,
    )

    # Plots
    if args.plots:
        os.makedirs(f"{basedir}/plots", exist_ok=True)
        if axis:
            if args.r and args.z:
                print(f"plots: r={args.r}, z={args.z}", flush=True)
                if len(args.r) == 2:
                    figaxs = {}  # create dict for fig and ax
                    for z in args.z:
                        # add plot for each z to dict
                        figaxs = plotOr(
                            reader,
                            args.r,
                            None,
                            z,
                            fieldunits,
                            ignored_keys,
                            basedir,
                            marker=args.plotsMarker,
                            axs=figaxs,
                            greyspace=args.greyspace,
                        )  # with r=[r1, r2], z: float
                    # plot every field with all z
                    showplot(figaxs, "-vs-r", basedir, show=(not args.save))
                    plt.close()
                if len(args.z) == 2:
                    figaxs = {}
                    for r in args.r:
                        figaxs = plotOz(
                            reader,
                            r,
                            None,
                            args.z,
                            fieldunits,
                            ignored_keys,
                            basedir,
                            marker=args.plotsMarker,
                            axs=figaxs,
                        )  # with r: float, z=[z1,z2]
                    showplot(figaxs, "-vs-z", basedir, show=(not args.save))
                    plt.close()
        elif dim == 3:
            if args.r and args.z:
                for r in args.r:
                    figaxs = {}
                    for z in args.z:
                        figaxs = plotTheta(
                            cellsize,
                            r,
                            z,
                            fieldunits,
                            ignored_keys,
                            basedir,
                            marker=args.plotsMarker,
                            axs=figaxs,
                        )
                    showplot(
                        figaxs,
                        f"-vs-theta-r={r}m",
                        basedir,
                        show=(not args.save),
                    )
                    plt.close()

                    if args.theta and len(args.z) == 2:
                        figaxs = {}
                        for theta in args.theta:
                            figaxs = plotOz(
                                reader,
                                r,
                                theta,
                                args.z,
                                fieldunits,
                                ignored_keys,
                                basedir,
                                marker=args.plotsMarker,
                                axs=figaxs,
                            )  # with r: float, z=[z1,z2]
                        showplot(
                            figaxs,
                            f"-vs-z-r={r}m",
                            basedir,
                            show=(not args.save),
                        )
                        plt.close()
                if args.theta and len(args.r) == 2:
                    for theta in args.theta:
                        figaxs = {}
                        for z in args.z:
                            figaxs = plotOr(
                                reader,
                                args.r,
                                theta,
                                z,
                                fieldunits,
                                ignored_keys,
                                basedir,
                                marker=args.plotsMarker,
                                axs=figaxs,
                                greyspace=args.greyspace,
                            )  # with r=[r1, r2], z: float
                        showplot(
                            figaxs,
                            f"-vs-r-theta={theta}deg",
                            basedir,
                            show=(not args.save),
                        )
                        plt.close()
        elif dim == 2:
            if args.r:
                if len(args.r) != 2 or not args.theta:
                    figaxs = {}
                    for r in args.r:
                        figaxs = plotTheta(
                            cellsize,
                            r,
                            None,
                            fieldunits,
                            ignored_keys,
                            basedir,
                            marker=args.plotsMarker,
                            axs=figaxs,
                        )
                    showplot(figaxs, "-vs-theta", basedir, show=(not args.save))
                    plt.close()

                if args.theta and len(args.r) == 2:
                    figaxs = {}
                    for theta in args.theta:
                        figaxs = plotOr(
                            cellsize,
                            args.r,
                            theta,
                            None,
                            fieldunits,
                            ignored_keys,
                            basedir,
                            marker=args.plotsMarker,
                            axs=figaxs,
                            greyspace=args.greyspace,
                        )  # with r=[r1, r2]
                    showplot(
                        figaxs,
                        f"-vs-r",
                        basedir,
                        show=(not args.save),
                    )
                    plt.close()

    # When dealing with elasticity
    suffix = ""
    cellsize_deformed = None
    datadict = resultinfo(cellsize, ignored_keys)
    found = False
    for field in list(reader.PointData.keys()):
        if field.endswith("displacement"):
            found = True
            break
    print(f"displacement found={found} in {list(reader.PointData.keys())}", flush=True)

    if found and (dim == 3 or axis):
        # make3Dview(cellsize, blockdata, key, color, addruler=True)
        if args.channels:
            os.makedirs(f"{basedir}/stl", exist_ok=True)
            print("Save stl for original geometries:", flush=True)
            for i, block in enumerate(blockdata.keys()):
                name = blockdata[block]["name"]
                actual_name = name.replace("/root/", "")
                print(f"\t{name}: actual_name={actual_name}", end="")
                if not actual_name.endswith("Isolant") and not "Air" in actual_name:
                    print(" saved", end="", flush=True)
                    extractBlock1 = ExtractBlock(registrationName=name, Input=cellsize)
                    extractBlock1.Selectors = [block]
                    extractBlock1.UpdatePipeline()
                    extractSurface1 = ExtractSurface(
                        registrationName="ExtractSurface1", Input=extractBlock1
                    )

                    print(f" file={basedir}/stl/{actual_name}.stl", flush=True)
                    SaveData(f"{basedir}/stl/{actual_name}.stl", proxy=extractSurface1)
                    Delete(extractBlock1)
                    del extractBlock1
                else:
                    print(" ignored", flush=True)

        geometry = deformed(cellsize, factor=args.deformedfactor)

        # compute channel deformation
        # use MeshLib see test-meshlib example
        if args.channels:
            geometryfactor1 = deformed(cellsize, factor=1)
            print("Save stl for deformed geometries:", flush=True)
            for i, block in enumerate(blockdata.keys()):
                name = blockdata[block]["name"]
                actual_name = name.replace("/root/", "")
                print(f"\t{name}: actual_name={actual_name}", end="")
                if not actual_name.endswith("Isolant") and not "Air" in actual_name:
                    print(" saved", flush=True)
                    extractBlock1 = ExtractBlock(
                        registrationName=name, Input=geometryfactor1
                    )
                    extractBlock1.Selectors = [block]
                    extractBlock1.UpdatePipeline()
                    extractSurface1 = ExtractSurface(
                        registrationName="ExtractSurface1", Input=extractBlock1
                    )

                    SaveData(
                        f"{basedir}/stl/{actual_name}-deformed.stl",
                        proxy=extractSurface1,
                    )
                    Delete(extractBlock1)
                    del extractBlock1
                else:
                    print(" ignored", flush=True)

        suffix = f"-deformed_factor{args.deformedfactor}"
        cellsize_deformed = geometry
    elif found and dim == 2 and not axis:
        cellsize_deformed = deformed(cellsize, factor=args.deformedfactor)

        suffix = f"-deformed_factor{args.deformedfactor}"
        # cellsize = geometry

    # Views
    if args.views:
        if not args.field:
            for vkey in list(cellsize.PointData.keys()) + list(
                cellsize.CellData.keys()
            ):

                if not vkey in ignored_keys:
                    if vkey in list(cellsize.CellData.keys()):
                        color = ["CELLS", vkey]
                    if vkey in list(cellsize.PointData.keys()):
                        color = ["POINTS", vkey]

                    makeview(
                        args,
                        cellsize,
                        blockdata,
                        vkey,
                        fieldunits,
                        color,
                        basedir,
                        suffix="",
                        addruler=False,
                        background=args.transparentBG,
                        customRangeHisto=args.customRangeHisto,
                    )

            if found:
                for vkey in list(cellsize_deformed.PointData.keys()) + list(
                    cellsize_deformed.CellData.keys()
                ):

                    if not vkey in ignored_keys:
                        if vkey in list(cellsize_deformed.CellData.keys()):
                            color = ["CELLS", vkey]
                        if vkey in list(cellsize_deformed.PointData.keys()):
                            color = ["POINTS", vkey]

                        makeview(
                            args,
                            cellsize_deformed,
                            blockdata,
                            vkey,
                            fieldunits,
                            color,
                            basedir,
                            suffix=suffix,
                            addruler=False,
                            background=args.transparentBG,
                            customRangeHisto=args.customRangeHisto,
                        )

        else:
            if args.field in list(cellsize.PointData.keys()) + list(
                cellsize.CellData.keys()
            ):
                if args.field in list(cellsize.CellData.keys()):
                    color = ["CELLS", args.field]
                if args.field in list(cellsize.PointData.keys()):
                    color = ["POINTS", args.field]
                makeview(
                    args,
                    cellsize,
                    blockdata,
                    args.field,
                    fieldunits,
                    color,
                    basedir,
                    suffix="",
                    addruler=False,
                    background=args.transparentBG,
                    customRangeHisto=args.customRangeHisto,
                )

            if found and (
                args.field
                in list(cellsize_deformed.PointData.keys())
                + list(cellsize_deformed.CellData.keys())
            ):
                if args.field in list(cellsize_deformed.CellData.keys()):
                    color = ["CELLS", args.field]
                if args.field in list(cellsize_deformed.PointData.keys()):
                    color = ["POINTS", args.field]
                makeview(
                    args,
                    cellsize_deformed,
                    blockdata,
                    args.field,
                    fieldunits,
                    color,
                    basedir,
                    suffix=suffix,
                    addruler=False,
                    background=args.transparentBG,
                    customRangeHisto=args.customRangeHisto,
                )

    # for magnetfield:
    #   - view contour for magnetic potential (see pv-contours.py)
    #   - view glyph for MagneticField
    #   - compute spherical expansion coefficients

    # # save vtkjs

    # # export view
    # ExportView('/home/LNCMI-G/trophime/export-scene.vtkjs', view=renderView1, ParaViewGlanceHTML='')


if __name__ == "__main__":
    sys.exit(main())

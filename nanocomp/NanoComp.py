from sys import exit as sysexit
import nanoget
from os import path
from argparse import ArgumentParser, FileType
from nanoplot import utils
import nanoplotter
import numpy as np
import logging
from .version import __version__


def main():
    '''
    Organization function
    -setups logging
    -gets inputdata
    -calls plotting function
    '''
    args = get_args()
    try:
        utils.make_output_dir(args.outdir)
        utils.init_logs(args, tool="NanoComp")
        args.format = nanoplotter.check_valid_format(args.format)
        sources = [args.fastq, args.bam, args.summary]
        sourcename = ["fastq", "bam", "summary"]
        if args.split_runs:
            split_dict = validate_split_runs_file(args.split_runs)
        datadf = nanoget.get_input(
            source=[n for n, s in zip(sourcename, sources) if s][0],
            files=[f for f in sources if f][0],
            threads=args.threads,
            readtype=args.readtype,
            names=args.names,
            combine="track")
        if args.raw:
            datadf.to_csv("NanoComp-data.tsv.gz", sep="\t", index=False, compression="gzip")
        if args.split_runs:
            change_identifiers(datadf, split_dict)
        make_plots(datadf, path.join(args.outdir, args.prefix), args)
        logging.info("Succesfully processed all input.")
    except Exception as e:
        logging.error(e, exc_info=True)
        raise


def get_args():
    epilog = """EXAMPLES:
    NanoComp --bam alignment1.bam alignment2.bam --outdir compare-runs
    NanoComp --fastq reads1.fastq.gz reads2.fastq.gz reads3.fastq.gz  --names run1 run2 run3
    """
    parser = ArgumentParser(
        description="Compares Oxford Nanopore Sequencing datasets.",
        epilog=epilog,
        formatter_class=utils.custom_formatter,
        add_help=False)
    general = parser.add_argument_group(
        title='General options')
    general.add_argument("-h", "--help",
                         action="help",
                         help="show the help and exit")
    general.add_argument("-v", "--version",
                         help="Print version and exit.",
                         action="version",
                         version='NanoComp {}'.format(__version__))
    general.add_argument("-t", "--threads",
                         help="Set the allowed number of threads to be used by the script",
                         default=4,
                         type=int)
    general.add_argument("-o", "--outdir",
                         help="Specify directory in which output has to be created.",
                         default=".")
    general.add_argument("-p", "--prefix",
                         help="Specify an optional prefix to be used for the output files.",
                         default="",
                         type=str)
    general.add_argument("--verbose",
                         help="Write log messages also to terminal.",
                         action="store_true")
    general.add_argument("--raw",
                         help="Store the extracted data in tab separated file.",
                         action="store_true")
    filtering = parser.add_argument_group(
        title='Options for filtering or transforming input prior to plotting')
    filtering.add_argument("--readtype",
                           help="Which read type to extract information about from summary. \
                             Options are 1D, 2D, 1D2",
                           default="1D",
                           choices=['1D', '2D', '1D2'])
    filtering.add_argument("--split_runs",
                           help="File: Split the summary on run IDs and use names in tsv file. "
                                "Mandatory header fields are 'NAME' and 'RUN_ID'.",
                           default=False,
                           type=FileType('r'),
                           metavar="TSV_FILE")
    visual = parser.add_argument_group(
        title='Options for customizing the plots created')
    visual.add_argument("-f", "--format",
                        help="Specify the output format of the plots.",
                        default="png",
                        type=str,
                        choices=['eps', 'jpeg', 'jpg', 'pdf', 'pgf', 'png', 'ps',
                                 'raw', 'rgba', 'svg', 'svgz', 'tif', 'tiff'])
    visual.add_argument("-n", "--names",
                        help="Specify the names to be used for the datasets",
                        nargs="+",
                        metavar="names")
    visual.add_argument("--plot",
                        help="Which plot type to use: boxplot or violinplot (default)",
                        type=str,
                        choices=['violin', 'box'],
                        default="violin")
    visual.add_argument("--title",
                        help="Add a title to all plots, requires quoting if using spaces",
                        type=str,
                        default=None)
    target = parser.add_argument_group(
        title="Input data sources, one of these is required.")
    mtarget = target.add_mutually_exclusive_group(
        required=True)
    mtarget.add_argument("--fastq",
                         help="Data is in default fastq format.",
                         nargs='+',
                         metavar="files")
    mtarget.add_argument("--summary",
                         help="Data is a summary file generated by albacore.",
                         nargs='+',
                         metavar="files")
    mtarget.add_argument("--bam",
                         help="Data as a sorted bam file.",
                         nargs='+',
                         metavar="files")
    args = parser.parse_args()
    if args.names:
        if not len(args.names) == [len(i) for i in [args.fastq, args.summary, args.bam] if i][0]:
            sysexit("ERROR: Number of names (-n) should be same as number of files specified!")
    return args


def validate_split_runs_file(split_runs_file):
    """Check if structure of file is as expected and return dictionary linking names to run_IDs."""
    try:
        content = [l.strip() for l in split_runs_file.readlines()]
        if content[0].upper().split('\t') == ['NAME', 'RUN_ID']:
            return {c.split('\t')[1]: c.split('\t')[0] for c in content[1:] if c}
        else:
            sysexit("ERROR: Mandatory header of --split_runs tsv file not found: 'NAME', 'RUN_ID'")
            logging.error("Mandatory header of --split_runs tsv file not found: 'NAME', 'RUN_ID'")
    except IndexError:
        sysexit("ERROR: Format of --split_runs tab separated file not as expected")
        logging.error("ERROR: Format of --split_runs tab separated file not as expected")


def change_identifiers(datadf, split_dict):
    """Change the dataset identifiers based on the names in the dictionary."""
    for rid, name in split_dict.items():
        datadf.loc[datadf["runIDs"] == rid, "dataset"] = name


def make_plots(df, path, args):
    df["log length"] = np.log10(df["lengths"])
    if args.plot == "violin":
        violin = True
    else:
        violin = False
    nanoplotter.output_barplot(
        df=df,
        figformat=args.format,
        path=path,
        title=args.title)
    nanoplotter.violin_or_box_plot(
        df=df,
        y="lengths",
        figformat=args.format,
        path=path,
        violin=violin,
        title=args.title)
    nanoplotter.violin_or_box_plot(
        df=df,
        y="log length",
        figformat=args.format,
        path=path,
        violin=violin,
        log=True,
        title=args.title)
    nanoplotter.violin_or_box_plot(
        df=df,
        y="quals",
        figformat=args.format,
        path=path,
        violin=violin,
        title=args.title)
    if args.bam:
        nanoplotter.violin_or_box_plot(
            df=df[df["percentIdentity"] > np.percentile(df["percentIdentity"], 1)],
            y="percentIdentity",
            figformat=args.format,
            path=path,
            violin=violin,
            title=args.title)


if __name__ == '__main__':
    main()

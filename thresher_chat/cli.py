#!/usr/bin/env python3
"""THRESHER-Chat CLI: Entry point with subcommands."""

# Import standard libraries and custom modules
import argparse
import shutil
import sys
import traceback

from thresher_chat.config import (
    DEFAULT_DB_DIR,
    DEFAULT_MODEL,
    VERSION,
)

AFFILIATION = (
    "Center for Microbial Medicine, Children's Hospital of Philadelphia; "
    "Philadelphia, PA, USA"
)

ASCII_ART = r"""
███████╗██╗  ██╗██████╗ ███████╗███████╗██╗  ██╗███████╗██████╗
╚═██╔══╝██║  ██║██╔══██╗██╔════╝██╔════╝██║  ██║██╔════╝██╔══██╗
  ██║   ███████║██████╔╝█████╗  ███████╗███████║█████╗  ██████╔╝
  ██║   ██╔══██║██╔══██╗██╔══╝  ╚════██║██╔══██║██╔══╝  ██╔══██╗
  ██║   ██║  ██║██║  ██║███████╗███████║██║  ██║███████╗██║  ██║
  ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                                 ██████╗██╗  ██╗ █████╗ ████████╗
                                ██╔════╝██║  ██║██╔══██╗╚══██╔══╝
                                ██║     ███████║███████║   ██║
                                ██║     ██╔══██║██╔══██║   ██║
                                ╚██████╗██║  ██║██║  ██║   ██║
                                 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
"""


def print_banner(term_width):
    """Print the centered THRESHER-Chat banner, version, and affiliation."""
    art_lines = ASCII_ART.strip("\n").splitlines()
    art_width = max(len(line) for line in art_lines)
    left_pad = " " * max((term_width - art_width) // 2, 0)

    print()
    for line in art_lines:
        print(left_pad + line.rstrip())
    print(f"Version {VERSION}".center(term_width))
    print(AFFILIATION.center(term_width))
    print()


def print_section(title, term_width):
    """Print a full-width separator block with a centered title."""
    print()
    print("=" * term_width)
    print(title.center(term_width))
    print("=" * term_width)


# Subcommand: ingest
def add_ingest_parser(subparsers):
    """Register the 'ingest' subcommand."""
    parser = subparsers.add_parser(
        "ingest",
        help="Index the THRESHER repository into a ChromaDB vector store.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo", required=True, help="Path to the THRESHER repository"
    )
    parser.add_argument(
        "--db-dir", default=DEFAULT_DB_DIR,
        help=f"Vector DB directory (default: {DEFAULT_DB_DIR})",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"LLM model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--embed-model", default=None,
        help="Override default embedding model",
    )
    parser.set_defaults(func=run_ingest)


def run_ingest(args):
    """Execute the ingest subcommand."""
    from thresher_chat.ingest import run
    return run(args)


# Subcommand: chat
def add_chat_parser(subparsers):
    """Register the 'chat' subcommand."""
    parser = subparsers.add_parser(
        "chat",
        help="Start the chatbot.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db-dir", required=True,
        help="Path to the vector DB directory (created by 'thresher-chat ingest')",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override default LLM model",
    )
    parser.add_argument(
        "--embed-model", default=None,
        help="Override default embedding model",
    )
    parser.add_argument(
        "--no-sources", action="store_true",
        help="Don't show source files for each answer",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug mode (prints retrieved context)",
    )
    parser.set_defaults(func=run_chat)


def run_chat(args):
    """Execute the chat subcommand."""
    from thresher_chat.chat import run
    return run(args)


# Subcommand: server
def add_server_parser(subparsers):
    """Register the 'server' subcommand."""
    parser = subparsers.add_parser(
        "server",
        help="Start the Flask web UI server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db-dir", required=True,
        help="Path to the vector DB directory (created by 'thresher-chat ingest')",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=5000,
        help="Port to bind to (default: 5000)",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override default LLM model",
    )
    parser.add_argument(
        "--embed-model", default=None,
        help="Override default embedding model",
    )
    parser.set_defaults(func=run_server)


def run_server(args):
    """Execute the server subcommand."""
    from thresher_chat.server import run
    return run(args)


# Parser construction
def build_parser():
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="thresher-chat",
        description=(
            "THRESHER-Chat: Local offline AI assistant for the THRESHER "
            "phylogenomics toolkit."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"THRESHER-Chat {VERSION}",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    add_ingest_parser(subparsers)
    add_chat_parser(subparsers)
    add_server_parser(subparsers)

    return parser


# Main entry point
def main():
    """Main entry point for THRESHER-Chat CLI"""

    term_width = shutil.get_terminal_size((80, 20)).columns
    print_banner(term_width)

    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand is None:
        parser.print_help()
        return 1

    print(f"THRESHER-Chat Mode: {args.subcommand}".center(term_width))

    try:
        print_section(f"Launching THRESHER-Chat {args.subcommand}", term_width)

        # Force flush all pending prints before handing off to the subcommand
        sys.stdout.flush()
        sys.stderr.flush()

        returncode = args.func(args)
        returncode = 0 if returncode is None else int(returncode)

        if returncode == 0:
            print_section(
                f"THRESHER-Chat Mode: {args.subcommand} completed successfully!",
                term_width,
            )
        else:
            print_section(
                f"THRESHER-Chat Mode: {args.subcommand} failed with return code {returncode}",
                term_width,
            )
        print()

        return returncode

    # Handle exceptions and print error messages for debugging purposes
    except KeyboardInterrupt:
        print()
        print(f"\033[93mTHRESHER-Chat Mode: {args.subcommand} interrupted by user.\033[0m")
        return 130
    except FileNotFoundError as e:
        print(f"File Not Found Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        print("\nTraceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
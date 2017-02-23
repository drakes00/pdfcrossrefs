#!/usr/bin/env python3


import os
import ast
import logging as log
import argparse
import subprocess


def execw(cmd):
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        shell=True
    ).communicate()


class PDF(object):
    def __init__(self, pdfdir=None, filename=None):
        if pdfdir is not None and filename is not None:
            self.pdfdir = pdfdir
            self.filename = filename
            self.fullpath = pdfdir+"/"+filename

            tmp = filename.strip(".pdf").split("_")
            self.name = tmp[-1] # TODO Rearange dashes and caps.
            self.author = tmp[0][:-2]
            self.year = int("20"+tmp[0][-2:]) # TODO 19XX?

            self.pages = int(execw(
                "pdftk \"{}\" dump_data | grep NumberOfPages".format(self.fullpath),
            )[0].decode("utf-8").strip("\n").split(" ")[1])
            self.free = "nonfree" not in filename

            # Guided attributes
            self.norm = None
            self.stepByStep = None
            self.scope = None
            self.targetedIndustry = None
            self.protocolSpecific = None
            self.indusAuthors = None
            self.govAuthors = None
            self.crossRefs = None


    def toDict(self):
        return vars(self)


    @ classmethod
    def fromDict(cls, varDict):
        res = PDF()
        for key,val in varDict.items():
            setattr(res, key, val)

        return res


    def guided(self):
        def _parse(res):
            if res in ("y", "Y"):
                return True
            elif res in ("n", "N"):
                return False
            else:
                return res


        log.info("\t[+] Please input metadata for PDF: {}".format(self.name))
        for attr in vars(self).keys():
            if getattr(self, attr) is None:
                res =  _parse(input("\t\t- {}: ".format(attr)))
                setattr(self, attr, res)
            else:
                print(getattr(self, attr))


def parsePdfs(pdfdir, noMetadata, guided):
    res = []

    if noMetadata:
        log.debug("[+] Ignoring cache.")
    else:
        try:
            log.debug("[+] Try loading metadata.")
            with open(pdfdir+"/metadata", "r") as handle:
                metadata = filter(None, [_.strip("\n") for _ in handle.readlines()])

            for line in metadata:
                pdf = PDF.fromDict(ast.literal_eval(line))
                res += [pdf]

            log.debug("[+] Done loading metadata.")
        except FileNotFoundError:
            log.debug("[-] No metadata found, parsing all PDFs.")

    log.debug("[+] Loading non chached PDFs.")
    for filename in filter(lambda f:f.endswith(".pdf"), os.listdir(pdfdir)):
        if all([pdf.filename != filename for pdf in res]):
            pdf = PDF(pdfdir, filename)
            res += [pdf]

    if guided:
        log.debug("[+] Entering guided mode.")
        for pdf in res:
            pdf.guided()

    return res


def main():
    argParser = argparse.ArgumentParser()
    argParser.add_argument(
        "--verbose", "-v",
        help="verbose mode",
        action="store_true"
    )

    argParser.add_argument(
        "--no-metadata", "-n",
        help="do not load metadata file",
        action="store_true"
    )

    argParser.add_argument(
        "--guided", "-g",
        help="semi-automatic mode",
        action="store_true"
    )

    argParser.add_argument(
        "--crossrefs", "-c",
        help="compute crossrefs between PDFs",
        action="store_true"
    )

    argParser.add_argument(
        "pdfdir",
        help="directory containing all PDF files to analyze",
        type=str
    )

    args = argParser.parse_args()
    if args.verbose:
        log.basicConfig(format="%(message)s", level=log.DEBUG)
    else:
        log.basicConfig(format="%(message)s", level=log.INFO)

    pdfs = parsePdfs(args.pdfdir, args.no_metadata, args.guided)
    with open(args.pdfdir+"/metadata", "w") as handle:
        handle.write("\n".join([str(pdf.toDict()) for pdf in pdfs])+"\n")


if __name__ == "__main__":
    main()

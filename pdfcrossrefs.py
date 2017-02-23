#!/usr/bin/env python3


import os
import ast
import logging as log
import argparse
import colorama
import subprocess
import collections


GUIDED = False


def parseInput(res):
    if res in ("y", "Y"):
        return True
    elif res in ("n", "N"):
        return False
    else:
        return res


def execw(cmd):
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        shell=True
    ).communicate()


class PDF(object):
    def __init__(self, pdfdir=None, filename=None):
        # Guided attributes
        self.pdfdir = None
        self.filename = None
        self.fullpath = None
        self.name = None
        self.searchname = None
        self.author = None
        self.year = None
        self.pages = None
        self.free = None
        self.norm = None
        self.stepByStep = None
        self.scope = None
        self.targetedIndustry = None
        self.protocolSpecific = None
        self.indusAuthors = None
        self.govAuthors = None
        self.crossrefs = collections.defaultdict(lambda: None)

        if pdfdir is not None and filename is not None:
            self.pdfdir = pdfdir
            self.filename = filename
            self.fullpath = pdfdir+"/"+filename

            tmp = filename.strip(".pdf").split("_")
            self.name = tmp[-1] # TODO Rearange dashes and caps.
            self.author = tmp[0][:-2]
            self.year = "20"+tmp[0][-2:] # TODO 19XX?

            self.pages = execw(
                "pdftk \"{}\" dump_data | grep NumberOfPages".format(self.fullpath),
            )[0].decode("utf-8").strip("\n").split(" ")[1]


    def toDict(self):
        varDict = vars(self)
        varDict.update(dict(varDict["crossrefs"]))
        return varDict


    @ classmethod
    def fromDict(cls, varDict):
        res = PDF()
        for key,val in varDict.items():
            setattr(res, key, val)

        return res


    def guided(self):

        log.info("\t[+] Please input metadata for PDF: {}".format(self.name))
        for attr in vars(self).keys():
            if getattr(self, attr) is None:
                res =  parseInput(input("\t\t[+] {}: ".format(attr)))
                if res != "":
                    setattr(self, attr, res)
            else:
                log.info(colorama.Fore.RED+"\t\t[-] Skipping attribure: {}".format(attr)+colorama.Style.RESET_ALL)


    def updateCrossrefs(self, other):
        if GUIDED:
            log.info("\t[+] Searching for crossrefs of \"{}\" in \"{}\".".format(other, self.name))
            res = input("\t\t[+] Change searched name (leave blank to keep) : ")
            if res:
                other = res
                log.info(colorama.Fore.BLUE+"\t\t[+] Now searching for crossrefs of \"{}\" in \"{}\".".format(other, self.name)+colorama.Style.RESET_ALL)
        else:
            log.debug("\t[+] Searching for crossrefs of \"{}\" in \"{}\".".format(other, self.name))

        res,_ = execw("pdfgrep \"{}\" \"{}\"".format(other, self.fullpath))
        res = res.decode("utf-8")
        confirm = res != ""
        if GUIDED:
            if res:
                log.info(colorama.Fore.BLUE+"\t\t[+] Occurences found :"+colorama.Style.RESET_ALL)
                log.info("\n"+res)
                confirm = bool(parseInput(input("Is it a crossref [y/n] : ")))
            else:
                log.info(colorama.Fore.RED+"\t\t[-] No occurences found."+colorama.Style.RESET_ALL)

        if confirm:
            log.debug(colorama.Fore.BLUE+"\t\t[+] Added crossref of \"{}\" in \"{}\".".format(other, self.name)+colorama.Style.RESET_ALL)
            self.crossrefs[other] = True
        else:
            log.debug(colorama.Fore.RED+"\t\t[+] Added NO crossref of \"{}\" in \"{}\".".format(other, self.name)+colorama.Style.RESET_ALL)
            self.crossrefs[other] = False


def parsePdfs(pdfdir, noMetadata):
    log.info("[+] Loading PDF info.")
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

    if GUIDED:
        log.debug("[+] Entering guided mode.")
        for pdf in res:
            pdf.guided()

    return res


def computeCrossrefs(pdfs):
    log.info("[+] Computing crossrefs.")
    for pdf in pdfs:
        for other in [_ for _ in pdfs if _ != pdf]:
            pdf.updateCrossrefs(other.searchname)


def main():
    global GUIDED

    colorama.init()
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

    if args.guided:
        GUIDED = True

    pdfs = parsePdfs(args.pdfdir, args.no_metadata)
    if args.crossrefs:
        computeCrossrefs(pdfs)

    with open(args.pdfdir+"/metadata", "w") as handle:
        handle.write("\n".join([str(pdf.toDict()) for pdf in pdfs])+"\n")


if __name__ == "__main__":
    main()

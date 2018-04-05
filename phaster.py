#!/usr/bin/env python
__author__ = "Fredrik Boulund"
__date__ = "2018"
__doc__ = """Utility functions to submit and query jobs via phaster.ca/phaster_api."""

from sys import argv, exit
import os.path
import argparse
import logging
import datetime
 
import requests


def parse_args():
    """Parse command line arguments."""

    desc = __doc__ + ". " + __author__ + " " + __date__
    parser = argparse.ArgumentParser(description=desc)
    
    parser.add_argument("-f", "--fasta", 
            default="",
            help="FASTA with genome sequence")
    parser.add_argument("-c", "--contigs", dest="contigs", action="store_true",
            default=False,
            help="Input is a multicontig assembly file [%(default)s].")
    parser.add_argument("-g", "--get-status", dest="get_status", action="store_true",
            default=False,
            help="Get status of submitted jobs stored in DB, will output results to OUTFILE if job is finished.")
    parser.add_argument("-o", "--outfile", dest="outfile", metavar="OUTFILE",
            default="phaster_results.zip",
            help="Output filename for finished results [%(default)s].")
    parser.add_argument("-d", "--database", metavar="DB", 
            default="phaster_jobs.tsv",
            help="Tab separated database of submitted jobs [%(default)s].")
    parser.add_argument("-u", "--url", dest="url",
            default="http://phaster.ca/phaster_api",
            help="URL to API endpoint [%(default)s].")
    
    if len(argv) < 2:
        parser.print_help()
        exit(1)

    options = parser.parse_args()

    return options


def read_database(database):
    """Read tab-separated database file into dict."""
    db = {}
    if os.path.isfile(database):
        with open(database) as f:
            for line in f:
                filename, job_id, status, date = line.split("\t")
                db[job_id] = (filename, status, date)
    else:
        with open(database, 'w') as f:
            pass
    return db


def write_database(db, database_file):
    """Write updated database to file."""
    with open(database_file, 'w') as f:
        for job_id, (filename, status, date) in db.items():
            f.write("{}\t{}\t{}\t{}\n".format(filename, job_id, status, date))
        

def submit_job(fasta_file, api_endpoint, options):
    """Submit fasta_file."""

    files = {"post-file": open(fasta_file, 'rb')}

    r = requests.post(api_endpoint, files=files, data=options)

    print("Post request response code:", r.status_code)
    r_dict = r.json()
    for key, value in r_dict.items():
        print("  {}: {}".format(key, value))
    return r_dict["job_id"], r_dict["status"], datetime.datetime.now()


def get_status(accession, api_endpoint, outfile):
    """Get status of submitted job."""

    payload = {"acc": accession}
    r = requests.get(api_endpoint, params=payload)
    
    print("Get request response code:", r.status_code)

    r_dict = r.json()
    for key, value in r_dict.items():
        print("  {}: {}".format(key, value))
    if "submissions ahead of yours" in r_dict["status"]:    
        print("Still waiting...")
    elif "Running" in r_dict["status"]:
        print("Still waiting...")
    elif "zip" in r_dict:
        print("Submission", accession, "appears to be finished!")
        print(r_dict["summary"])
        with open(outfile, 'wb') as outf:
            outf.write(r.text)
            print("Wrote output to:", outfile)
    return r_dict["job_id"], r_dict["status"], datetime.datetime.now()


if __name__ == "__main__":
    options = parse_args()

    db = read_database(options.database)

    if options.fasta:
        job_id, status, date = submit_job(options.FASTA, options.url, {"contigs": int(options.contigs)})
        db[job_id] = (options.FASTA, status, date)
    elif options.get_status:
        for job_id, (filename, status, date) in db.items():
            job_id, status, date = get_status(job_id, options.url, options.outfile)
            db[job_id] = (filename, status, date)
    write_database(db, options.database)


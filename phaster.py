#!/usr/bin/env python
__author__ = "Fredrik Boulund"
__date__ = "2018"
__doc__ = """Utility script to submit, query ongoing jobs, and download results via phaster.ca/phaster_api."""

from sys import argv, exit
import os
import argparse
import logging
import datetime
import time
 
import requests

def parse_args():
    """Parse command line arguments."""

    desc = __doc__ + " " + __author__ + " (c) " + __date__ + "."
    parser = argparse.ArgumentParser(description=desc)
    
    parser.add_argument("-f", "--fasta", metavar="FILE", dest="fasta", nargs="+",
            default="",
            help="FASTA file with genome sequence")
    parser.add_argument("-c", "--contigs", dest="contigs", action="store_true",
            default=False,
            help="Input is a multicontig assembly file [%(default)s].")
    parser.add_argument("-g", "--get-status", dest="get_status", action="store_true",
            default=False,
            help="Get status of submitted jobs stored in DB, "
                 "will automatically download results if job is finished.")
    parser.add_argument("-d", "--database", metavar="DB", 
            default="phaster_jobs.tsv",
            help="Tab separated database of submitted jobs [%(default)s].")
    parser.add_argument("-u", "--url", dest="url",
            default="http://phaster.ca/phaster_api",
            help="URL to API endpoint [%(default)s].")
    parser.add_argument("-w", "--wait", metavar="W", dest="wait",
            default=10,
            help="Wait for W seconds between each API request [%(default)s].")
    parser.add_argument("--loglevel", 
            choices=["DEBUG", "INFO"],
            default="INFO",
            help="Set loglevel [%(default)s].")

    if len(argv) < 2:
        parser.print_help()
        exit(1)

    options = parser.parse_args()

    logfmt = "%(asctime)s %(levelname)s: %(message)s"
    if options.loglevel == "INFO":
        logging.basicConfig(format=logfmt, level=logging.INFO)
    elif options.loglevel == "DEBUG":
        logging.basicConfig(format=logfmt, level=logging.DEBUG)

    return options


def read_database(database):
    """Read tab-separated database file into dict."""
    db = {}
    if os.path.isfile(database):
        with open(database) as f:
            for line in f:
                filename, job_id, status, date = line.strip().split("\t")
                db[job_id] = (filename, status, date)
        logging.debug("Read %s existing entries from %s", len(db), database)
    else:
        logging.debug("Database %s does not exists, creating...", database)
        open(database, 'w').close()
        logging.debug("Created empty database %s", database)
    return db


def write_database(db, database_file):
    """Write updated database to file."""
    with open(database_file, 'w') as f:
        for job_id, (filename, status, date) in db.items():
            f.write("{}\t{}\t{}\t{}\n".format(filename, job_id, status, date))


def submit_job(fasta_file, api_endpoint, options):
    """Submit fasta_file."""

    files = {"post-file": open(os.path.abspath(fasta_file), 'rb')}

    r = requests.post(api_endpoint, files=files, data=options)

    if r.status_code != 200:
        logging.error("Submission of %s failed!", fasta_file)
        logging.error(r.text)
        return "Failed", "Submission failed", datetime.datetime.now()
    logging.info("Submission of %s appears successful", fasta_file)

    r_dict = r.json()
    for key, value in r_dict.items():
        logging.info("  {}: {}".format(key, value))
    return r_dict["job_id"], r_dict["status"], datetime.datetime.now()


def get_status(accession, api_endpoint, query_filename):
    """Get status of submitted job, download if finished."""

    payload = {"acc": accession}
    r = requests.get(api_endpoint, params=payload)

    if r.status_code != 200:
        logging.error("Get request for status of job id %s failed", accession)
        return accession, "Get request failed", datetime.datetime.now()

    r_dict = r.json()
    job_status = r_dict["status"]
    if "submissions ahead of yours" in job_status:
        logging.info("Job %s still waiting: %s", accession, job_status)
    elif "Running" in r_dict["status"]:
        logging.info("Job %s currently running: %s", accession, job_status)
    elif "zip" in r_dict:
        logging.info("Job %s appears to be finished!", accession)
        try:
            download_and_write_results(r_dict, query_filename)
            job_status = "Completed and downloaded"
        except IOError as e:
            logging.error("An error occured when trying to download the results for %s", accession)
            logging.error(e)
    return r_dict["job_id"], job_status, datetime.datetime.now()


def download_and_write_results(response_dict, query_filename):
    """Write results for finished jobs."""

    query_basename = query_filename.split(".")[0]
    try:
        os.mkdir(query_basename)
    except OSError:
        logging.warning("Output directory %s already exists, skipping download of results.", query_basename)
        return 

    summary_filename = os.path.join(query_basename, query_basename+".phaster_summary.txt")
    zip_filename = os.path.join(query_basename, query_basename+".phaster_results.zip")

    with open(summary_filename, 'w') as summary_file:
        summary_file.write(response_dict["summary"])
        logging.info("Wrote summary to: %s", summary_filename)
    
    zip_response = requests.get("http://"+response_dict["zip"], stream=True)
    if zip_response.status_code == 200:
        with open(zip_filename, 'wb') as zip_file:
            zip_file.write(zip_response.content)
            logging.info("Downloaded results to: %s", zip_filename)
    else:
        raise IOError("Request for zip file {} failed".format(response_dict["zip"]))


if __name__ == "__main__":
    options = parse_args()

    db = read_database(options.database)

    if options.fasta:
        for fasta in options.fasta:
            job_id, status, date = submit_job(fasta, options.url, {"contigs": int(options.contigs)})
            db[job_id] = (fasta, status, date)
            time.sleep(options.wait)
    elif options.get_status:
        for job_id, (filename, status, date) in db.items():
            if job_id == "Failed":
                continue
            output_filename = os.path.basename(filename)
            job_id, status, date = get_status(job_id, options.url, output_filename)
            db[job_id] = (filename, status, date)
            time.sleep(options.wait)
    write_database(db, options.database)


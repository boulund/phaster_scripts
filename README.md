# PHASTER scripts
Small utility scripts to query the PHASTER API endpoint.

Run the script without arguments or with `-h`/`--help` to see a list of
available options.  The script creates a small local database in a tab
separated file called `phaster_jobs.tsv`, where it stores date and time of most
recent API query attempt, along with the last observed job status for each
submitted file. The name of the database file can be modified with the
`-d`/`--database` argument.


## Submit a job with a single complete genome sequence
It is very simple to submit a single complete genome sequence to PHASTER using
the script:

```
$ ./phaster.py --fasta path/to/genome.fasta
```

This will submit the sequence file to the online API and store the submission
in the database file. The information in the database file is required to keep
track of submission job IDs, so results can be downloaded when the submitted
job is finished.


## Submit a job with a draft genome assembly (several contigs)
The PHASTER API needs to know if the input file contains multiple sequences
(contigs), so the script will include this information if you use the
`-c`/`--contigs` argument:

```
$ ./phaster.py --contigs --fasta path/to/genome.fasta
```

## Query previously submitted job(s)
Running with the `-g`/`--get-status` argument will automatically query the
status of all previously jobs listed in the database:

```
$ ./phaster.py --get-status
```





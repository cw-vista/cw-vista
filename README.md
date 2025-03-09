# The CW Vista: Depth vs Breadth of Continuous Gravitational Wave Searches

This repository contains code and data for generating *vista plots*: plots of
the sensitivity depth versus the parameter-space breadth of searches for
continuous gravitational waves (CWs). See [Wette (2023)][wette2023] and
references therein for further information.

The vista plots are generated by a [Streamlit][streamlit] webapp hosted
[here][webapp].

## Contributing

If you have published a CW search, please contribute your results and keep the
CW vista up-to-date. To contribute a new CW search:

1. Fork the [`cw-vista` repository][repo] on GitHub.

2. Check out your fork locally with `git clone`.

3. Set up your local checkout. You will need to install [pre-commit][pre-commit]
   which will run scripts to verify that the new CW search data is in the
   required format. This can be done by running the following commands:

   ```bash
   $ pip install pre-commit   # or install via conda, apt-get, etc.
   $ cd cw-vista/
   $ pre-commit install
   pre-commit installed at .git/hooks/pre-commit
   ```

   (You only need to do this once.)

4. Create a new branch for your changes, e.g.:

   ```bash
   $ git checkout -b my-cw-search main
   ```

5. Run the following script:

   ```bash
   $ ./add-new-cw-search
   ```

   This script will set up a file for a new CW search at
   `cw_search_data/unpublished.json`. (Don't worry about the file name, this
   will be updated later.)

6. Open `cw_search_data/unpublished.json` in your favourite editor, and start
   filling in the fields. CW search results are recorded as [JSON][json]
   files. See the next section for a guide to what information is required.

7. Once you have completed the entries in `cw_search_data/unpublished.json`, run:

   ```bash
   $ git add -A cw_search_data/
   $ pre-commit
   ```

   This will run checks that the entries are in the correct format. Please
   correct any errors.  **Note:** if you have entered publication details for
   your search, `pre-commit` will rename the JSON file from `unpublished.json`
   to a unique name consistent with a short BibTeX key. You should save any
   changes to `unpublished.json` and close your editor before running the above
   commands, and then re-open the file under its new name.

8. Once `pre-commit` no longer reports any error, commit your changes to the Git repository:

   ```bash
   $ git add -A cw_search_data/
   $ git commit
   ```

9. Push your changes to your fork on GitHub:

   ```bash
   $ git push origin my-cw-search
   ```

10. Open a pull request on GitHub to merge your changes into the [main
    repository](repo).

## CW Search Data JSON Format

CW search results are recorded as [JSON][json] files. The top-level of the file
is a JSON record which must have the following fields:

```json
{
    "reference": ...,
    "searches": ...
}
```

* The `reference` field is initially set to the string `unpublished`. In this way
  you can already enter data for a CW search before it has been published. Once
  it is published, you can replace this field with a record containing the usual
  BibTeX fields:

  ```json
  "reference": {
      "author": ["first, author", "second, author", ...],
      "title": ...,
      "journal": ...,
      "volume": ...,
      "pages": ...,
      "year": ...,
      "doi": ...
  }
  ```

  One final field is required: `key-suffix`. This is a single lower-case letter
  (`[a-z]`) which ensures that each BibTeX key is unique. For example, Einstein
  would use `"key-suffix": "a"` for his first paper published in 1905, `"b"` for
  his second paper, etc.

* The `searches` field is a list, and each element of the list is a record
  representing a search:

  ```json
  "searches": [
      {
          "category": ...,
          "astro-target": ...,
          "obs-run": ...,
          "algorithm-coherent": ...,
          "algorithm-incoherent": ...,
          "time-span": ...,
          "max-coherence-time": ...,
          # EITHER:
              "depth": ...,
          # OR:
              "depth-h0": ...,
              "depth-freq": ...,
              "depth-Sh-obs-det": ...,
          "param-space": ...
      },
      ...
  ]
  ```

  Fields are *required* unless otherwise stated:

  * `category`: category of the CW search. This will be filled out when you ran
    the `./add-new-cw-search` script.

  * `obs-run`: LIGO/Virgo/KAGRA observing run of the data analysed, e.g. `O3`,
    `O4`, etc. If data from multiple observing runs was used, the latest
    observing run should be entered.

  * `astro-target`(*optional*): if your search targeted a particular
    astronomical object, please enter its astronomical name here. Please use
    common/abbreviated names where appropriate, e.g. `Crab`, `Cas A`, otherwise
    use the standard astronomical names e.g. `PSR Jhhmm+-ddmm` for pulsars,
    `Gd.d+-d.d` for supernovae, etc.

  * `algorithm-coherent`: Algorithm used for the coherent part of the CW
    search. Use `power` if your search uses the power in a short Fourier
    transform as the coherent part of the analysis. Other options are
    `5-vectors`,`F-statistic` for the $\mathcal{F}$-statistic, and
    `Bayesian`. New methods may be added by editing the `algorithm-coherent`
    section of the JSON file `label_map.json`.

  * `algorithm-incoherent`: Algorithm used of the incoherent part of the CW
    search, i.e. when combining together coherent segments. For a fully-coherent
    analysis, use `none`, otherwise a list of algorithms is given in the
    `algorithm-coherent` section of the JSON file `label_map.json`. New methods
    may be added.

  * `time-span`: Total time-span of all the data analysed in the search, in
    seconds. This includes not only the data analysed, but any gaps in the data
    as well. Put another way, it is the difference between the timestamp of the
    last data sample analysed, and the timestamp of the first data sample
    analysed.

  * `max-coherence-time`: Maximum time-span of any data that was coherently
    analysed, in seconds. This may be, for example, the time-base of a short
    Fourier transform, or the time-span of segments of data analysed with the
    $\mathcal{F}$-statistic.

  * `depth`: Sensitivity depth achieved by your search. This may be specified in
    one of two ways:

    * If a field `depth` is given, its value is simply used.

    * Otherwise, the sensitivity depth is computed using the following fields:

      * `depth-h0`: $h_0$ upper limit to use for the depth.

      * `depth-freq`: frequency at which the $h_0$ upper limit was placed.

      * `depth-Sh-obs-det`: a list of strings of the form `<observing
        run>-<detector>` which specify the detector noise curve to use to
        compute the noise floor $S_h$ for the depth. For example, `O3a-H1`
        specifies data from the LIGO Hanford detector recording during the first
        part of the 3rd observing run. See the directory `noise_curves/` for a
        complete list of available noise curves.

* The `param-space` field of `searches` describes the parameter-space of the
  search, this will be used to compute the parameter-space breadth.

  * For targeted searches for known pulsars, this field should simply state the
    number of pulsars searched for:

    ```json
    "param-space": {
        "num-pulsars": ...
    }
    ```

  * For all other searches, it should be a record with the following fields:

    ```json
    "param-space": {
        "sky-fraction": ...,
        "hmm-num-jumps": ...,
        "ranges": [
            {
                    "freq": [minimum, maximum],
                ...
            },
            ...
        ]
    }
    ```

    Fields are:

    * `sky-fraction` (*optional*) : Fraction of the sky covered by the search,
      in the range `(0,1]`. All-sky searches should use `1`. Directed searches
      at single points on the sky should omit this field.

    * `hmm-num-jumps` (*optional*): For searches using a hidden Markov model,
      this is the maximum number of jumps the model is allowed to make after
      each time step.

    * `ranges` (*required*): This field is a list, and each element of the list
      presents a subspace of the parameter space in frequency, spin-down, and (if
      appropriate) binary orbital parameters. Each subspace of the parameter
      space must be representable by simple minimum/maximum ranges in each
      parameter; for more complicated parameter space, average/representative
      ranges may be given. Support parameter ranges are *optional* unless stated
      otherwise:

      * `freq` (*required*): frequency;

      * `fdot`: first spin-down;

      * `fddot`: second spin-down;

      * `bin-period`: binary orbital period

      * `bin-a-sin-i` (also requires `bin-period`): binary orbit, projected semi-major axis.

      * `bin-time-asc`: binary orbit, time of ascension.

      * `bin-freq-mod-depth`: binary orbit, frequency modulation depth (as used
        by the TwoSpect algorithm).

      Parameter-space breadths are calculated separately for each subspace given
      in `ranges`, and are then summed to give the total breadth of the search.

## Running the Webapp Locally

You can run the webapp locally as follows:

1. Clone the [`cw-vista` repository][repo], or your fork thereof.

2. Create a virtual environment with Python 3.10 and install requirements:

   ```bash
   $ cd cw-vista/
   $ python3.10 -m venv venv/
   $ source venv/bin/activate
   $ pip install -r requirements.txt
   ```

3. Run the webapp:

   ```bash
   $ streamlit run app.py
   ```


[json]:             https://www.json.org/
[pre-commit]:       https://pre-commit.com/
[repo]:             https://github.com/cw-vista/cw-vista/
[streamlit]:        https://streamlit.io/
[webapp]:           https://cw-vista.streamlit.app/
[wette2023]:        https://doi.org/10.1016/j.astropartphys.2023.102880

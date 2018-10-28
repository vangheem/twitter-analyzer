Twitter Analyzer
================

Did you ever want to be able to analyze your twitter account for things
you've liked or people who have trolled you? This is the tool for you.

Twitter does not provide any mechanism to search in depth your tweets
and timeline.


Requires: Python 3.5+
Twitter API consumer/access tokens and secrets


Installation
------------

With pip:

    pip install twitter-analyzer


Usage
-----

Initialize:

    tanalyze init


Update:

    tanalyze update


Find trolls:

    tanalyze find-trolls


Search

    tanalyze search github

Search urls

    tanalyze search github --url

Search users

    tanalyze search vangheezy --user

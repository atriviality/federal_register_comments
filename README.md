# Federal Register Comment Collector

This is a proof of concept that leverages the Federal Register API to consolidate comments for notices of proposed rule making (NPRM). The code does a second pass on the PDF that is created to add bookmarks as well as limited analysis of the text, i.e., a word cloud. 

## Usage

The document_id can be found under the Document ID box for a proposed rule. An API key for the Federal Register API can be obtained at (https://open.gsa.gov/api/regulationsgov/)[https://open.gsa.gov/api/regulationsgov/].

```
usage: retrieve_regulation_comments [-h] [--post-process] [--no-verify] document_id api_key

Retrieves comments from the

positional arguments:
  document_id
  api_key

options:
  -h, --help      show this help message and exit
  --post-process
  --no-verify
```

# Public Release

Approved for Public Release; Distribution Unlimited. Public Release Case Number 25-0060.

This (software/technical data) was produced for the U. S. Government under Contract Number 1331L523D130S0003, and is subject to Federal Acquisition Regulation Clause 52.227-14, Rights in Data—General, Alt. II, III and IV (DEC 2007) [Reference 27.409(a)].  

No other use other than that granted to the U. S. Government, or to those acting on behalf of the U. S. Government under that Clause is authorized without the express written permission of The MITRE Corporation. 

For further information, please contact The MITRE Corporation, Contracts Management Office, 7515 Colshire Drive, McLean, VA  22102-7539, (703) 983-6000.  

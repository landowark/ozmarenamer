#!/usr/bin/env python

import ozma
from ozma.setup import get_cliarg

params = get_cliarg()
ozma.main(filepath=params['filename'])
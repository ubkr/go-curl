#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import re

CURL_GIT_PATH = os.environ.get("CURL_GIT_PATH", './curl')

target_dirs = [
    '{}/include/curl'.format(CURL_GIT_PATH),
    '/usr/local/include',
    'libdir/gcc/target/version/include'
    '/usr/target/include',
    '/usr/include',
]

def get_curl_path():
    for d in target_dirs:
        for root, dirs, files in os.walk(d):
            if 'curl.h' in files:
                return os.path.join(root, 'curl.h')
    raise Exception("Not found")


opts = []
codes = []
infos = []
auths = []
opt_deprecated = []
opt_redefined = []

info_deprecated = []
info_redefined = []

init_pattern = re.compile(r'CURLOPT\(CURLOPT_(.*?),\s+CURLOPTTYPE_(LONG|OBJECTPOINT|FUNCTIONPOINT|STRINGPOINT|OFF_T|SLISTPOINT|CBPOINT|VALUES),\s+(\d+)\)')

error_pattern = re.compile('^\s+(CURLE_[A-Z_0-9]+),')
info_pattern = re.compile('^\s+(CURLINFO_[A-Z_0-9]+)\s+=')
opt_deprecated_pattern = re.compile(r'^\s+CURLOPTDEPRECATED\(CURLOPT_(.*?),(.*?)')
opt_redefined_pattern = re.compile('CURLOPT_[A-Z_0-9]+')

info_deprecated_pattern = re.compile(r'CURLINFO_(.*?) CURL_DEPRECATED\(')
info_deprecated_multiline_candidate_pattern = re.compile(r'CURL_DEPRECATED\(')
info_deprecated_multiline_pattern = re.compile(r'CURLINFO_([A-Z_0-9]+)')




with open(get_curl_path()) as f:
    #for line in f:
    lines = f.readlines()
    for line_iterator in range(len(lines)):
        line = lines[line_iterator]
        match = init_pattern.findall(line)
        if match:
            opts.append(match[0][0])
        if line.startswith('#define CURLOPT_'):
            o = line.split()
            opts.append(o[1][8:])  # strip :(

        if line.startswith('#define CURLAUTH_'):
            o = line.split()
            auths.append(o[1][9:])

        match = error_pattern.findall(line)
        if match:
            codes.append(match[0])

        if line.startswith('#define CURLE_'):
            c = line.split()
            codes.append(c[1])

        match = info_pattern.findall(line)
        if match:
            infos.append(match[0])

        if line.startswith('#define CURLINFO_'):
            i = line.split()
            if '0x' not in i[2]:  # :(
                infos.append(i[1])
        
        opt_deprecated_match = opt_deprecated_pattern.findall(line)
        if opt_deprecated_match:
            opt_deprecated.append(opt_deprecated_match[0][0])

        info_deprecated_match = info_deprecated_pattern.findall(line)
        info_deprecated_multiline_candidate_match = info_deprecated_multiline_candidate_pattern.findall(line)

        if info_deprecated_match:
            info_deprecated.append(info_deprecated_match[0])
        elif info_deprecated_multiline_candidate_match:
            #if we get a match here it means we need to look at the previous line
            info_multiline_match = info_deprecated_multiline_pattern.findall(lines[line_iterator - 1])
            if info_multiline_match:
                info_deprecated.append(info_multiline_match[0])

        opt_redefined_match = opt_redefined_pattern.findall(line)
        if opt_redefined_match:
            if len(opt_redefined_match) == 2:
                opt_redefined.append(opt_redefined_match)

template = """//go:generate /usr/bin/env python ./misc/codegen.py

package curl
/*
#include <curl/curl.h>
#include "compat.h"
*/
import "C"

// CURLcode
const (
{code_part}
)

// easy.Setopt(flag, ...)
const (
{opt_part}
)

// Deprecated
{opt_deprecated_part}

// Renamed
{opt_redefined_part}

// easy.Getinfo(flag)
const (
{info_part}
)

// Deprecated
{info_deprecated_part}

// Auth
const (
{auth_part}
)

// generated ends
"""

code_part = []
for c in codes:
    code_part.append("\t{:<25} = C.{}".format(c[4:], c))

code_part = '\n'.join(code_part)

opt_part = []
for o in opts:
    opt_part.append("\tOPT_{0:<25} = C.CURLOPT_{0}".format(o))

opt_part = '\n'.join(opt_part)

info_part = []
for i in infos:
    info_part.append("\t{:<25} = C.{}".format(i[4:], i))

info_part = '\n'.join(info_part)

auth_part = []
for a in auths:
    auth_part.append("\tAUTH_{0:<25} = C.CURLAUTH_{0} & (1<<32 - 1)".format(a))

auth_part = '\n'.join(auth_part)

opt_deprecated_part = []
for d in opt_deprecated:
    opt_deprecated_part.append("// OPT_{0:<25}\t\tDEPRECATED".format(d))

opt_deprecated_part = '\n'.join(opt_deprecated_part)

info_deprecated_part = []
for d in info_deprecated:
    info_deprecated_part.append("// INFO_{0:<25}\t\tDEPRECATED".format(d))

info_deprecated_part = '\n'.join(info_deprecated_part)


opt_redefined_part = []
for d in opt_redefined:
    opt_redefined_part.append("// {0:<25} -> {1}".format(d[0], d[1]))

opt_redefined_part = '\n'.join(opt_redefined_part)

with open('./const_gen.go', 'w') as fp:
    fp.write(template.format(**locals()))

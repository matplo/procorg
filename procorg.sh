#!/bin/bash
# Start the ProcOrg web interface

SAVEDIR=$(pwd)

function thisdir()
{
        SOURCE="${BASH_SOURCE[0]}"
        while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
          DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
          SOURCE="$(readlink "$SOURCE")"
          [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
        done
        DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
        echo ${DIR}
}
THISD=$(thisdir)

cd ${THISD}

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

procorg $@
if [ $? -ne 0 ]; then
    echo "Failed to start ProcOrg. Please check the error messages above."
    exit 1
fi

cd ${SAVEDIR}
#!/bin/bash

usage() {
    echo "$0 " >&2
    echo "           [-a|--add]         <add cups-pdf printer > " >& 2
    echo "           [-d|--del]      <delete cups-pdf printer > " >& 2
    echo "           [-c|--cfg] <set proper right for lpadmin > " >& 2
    echo "           [-l|--list]       <list cups-pdf printer > " >& 2
    echo "           [--num]          <number to add or delete> " >& 2
    echo "           [--min]          <index to add or delete>  " >& 2
    echo " EXAMPLE :                                            " >& 2
    echo " $0 -a --num 100"
    echo "   This will add 100 cups-pdf printer with default name testpdf1 to testpdf100"
}

# global variables
cfgFlag="false"
addFlag="false"
delFlag="false"
listFlag="false"
printerName='testpdf'
lpinfo='/usr/sbin/lpinfo'

cat /etc/issue | grep SUSE > /dev/null
onSuse=$?

setConfig() {
    # add lpadmin group
    sudo grep lpadmin /etc/group > /dev/null
    if [ $? -ne 0 ]; then
        sudo /usr/sbin/groupadd lpadmin
    fi
    # add current user to lpadmin group
    cuser=$(whoami)
    if [ $onSuse -eq 0 ]; then
        sudo /usr/sbin/usermod -G lpadmin $cuser
    else
        sudo usermod -a -G lpadmin $cuser
    fi
    # add lpadmin to SystemGroup on cups service
    sudo grep lpadmin  /etc/cups/cupsd.conf > /dev/null
    if [ $? -ne 0 ]; then
        sudo sed -i -e 's/^\(SystemGroup\)/\1 lpadmin/' /etc/cups/cupsd.conf
    fi
    # restart cups service
    sudo /sbin/service cups restart
    sudo /usr/sbin/service cups restart
    sleep 2
}

addPrinter() {
    host="hostname is $(hostname) installed with $(perl -wnl -e 'print $_ if /\S+/ and $.== 1' /etc/issue )"
    ppd=$(sudo /usr/sbin/lpinfo -l -m | grep -i cups-pdf|grep -i model|awk -F"=" '/.ppd/{print $2}')
    for i in $( seq $minIndex $number )
    do
        sudo /usr/sbin/lpadmin -p $printerName${i} -E -v cups-pdf:/ -m $ppd -L "$host" -D "cups-pdf printer"
    done
}

delPrinter() {
    for i in $( seq $minIndex $number )
    do
        sudo /usr/sbin/lpadmin -x $printerName${i}
    done
}

listPrinter() {
    lpstat -s
}

###################### main ######################
while [ $# -gt 0 ] ; do
    case "$1" in
    -a | [-]*add)
        addFlag="true"
        shift 1
        ;;
    -d | [-]*del)
        delFlag="true"
        shift 1
        ;;
    -c | [-]*cfg)
        cfgFlag="true"
        shift 1
        ;;
    -l | [-]*list)
        listFlag="true"
        shift 1
        break
        ;;

    [-]*num)
        number=$2
        shift 2
        break
        ;;

    [-]*min)
        minIndex=$2
        shift 2
        break
        ;;

    -- )
        shift
        break
        ;;

    -h | [-]*help)
        usage
        exit 0
        ;;

    *)
        echo "un-supported argumnents $@" >&2
        usage
        exit 1
        ;;

    esac
done

# add current user to lpadmin group first
if [ $cfgFlag = "true" ]; then
    setConfig
fi

# check for add or delete
if [ $addFlag = "false" ] && [ $delFlag = "false" ]; then
    addFlag="true"
    delFlag="false"
fi

if [ $listFlag = "true" ]; then
    listPrinter
    exit 0
fi

if [ ! $number ]; then
    number=100
fi

if [ ! $minIndex ]; then
    minIndex=1
fi

if [ $addFlag = "true" ]; then
    addPrinter
fi

if [ $delFlag = "true" ]; then
    delPrinter
fi


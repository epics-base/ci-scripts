/*************************************************************************\
* Copyright (c) 2020 ITER Organization.
* EPICS BASE is distributed subject to a Software License Agreement found
* in file LICENSE that is included with this distribution.
\*************************************************************************/

/*
 *  Author: Ralph Lange <ralph.lange@gmx.de>
 */

#include <string.h>

#include <epicsUnitTest.h>
#include <testMain.h>

#include <dbAccess.h>
#include <dbStaticLib.h>
#include <errlog.h>

void exampleTest_registerRecordDeviceDriver(struct dbBase *);

static dbCommon *prec;

/* from Base 3.15 dbUnitTest.c */
static
dbCommon* testdbRecordPtr(const char* pv)
{
    DBADDR addr;

    if (dbNameToAddr(pv, &addr))
        testAbort("Missing record \"%s\"", pv);

    return addr.precord;
}

static void testOnce(void)
{
    testDiag("check that tests work");

    dbReadDatabase(&pdbbase, "exampleTest.dbd", "../O.Common", NULL);
    exampleTest_registerRecordDeviceDriver(pdbbase);
    dbReadDatabase(&pdbbase, "dbExample1.db", "../../../db", "user=test");

    testDiag("Searching for records from example application");

    prec = testdbRecordPtr("test:xxxExample");
    testOk((prec != NULL), "record test:xxxExample");

    prec = testdbRecordPtr("test:aiExample");
    testOk((prec != NULL), "record test:aiExample");
}

MAIN(exampleTest)
{
    testPlan(2);
    testOnce();
    return testDone();
}

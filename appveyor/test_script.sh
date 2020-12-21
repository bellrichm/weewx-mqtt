if [ "$ENABLED" != "true" ]; then
  exit 0
fi

if [ "$BUILDTYPE" = "LOCAL" ]; then
  HTML_OPTIONS=" --cover-html --with-html "
  PPATH="../weewx/bin/"
else
  PPATH="./weewx/bin/"  
fi

 PYTHONPATH=bin:$PPATH nosetests ./bin/user/tests --exe --exclude=setup --cover-package=user.mqttpublish --with-xunit --with-coverage --cover-branches --cover-xml --logging-level=ERROR --verbosity=1 $HTML_OPTIONS
 rc=$?
 
# ToDo - option to not exit on error - gor debugging
if [ $rc -ne 0 ]; then
  echo "$rc"
  exit $rc
fi

if [ "$BUILDTYPE" != "LOCAL" ]; then
  find "$APPVEYOR_BUILD_FOLDER" -type f -name 'nosetests.xml' -print0 | xargs -0 -I '{}' curl -F 'file=@{}' "https://ci.appveyor.com/api/testresults/junit/$APPVEYOR_JOB_ID"
fi
exit $rc

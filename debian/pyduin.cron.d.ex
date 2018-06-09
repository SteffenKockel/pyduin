#
# Regular cron jobs for the pyduin package
#
0 4	* * *	root	[ -x /usr/bin/pyduin_maintenance ] && /usr/bin/pyduin_maintenance

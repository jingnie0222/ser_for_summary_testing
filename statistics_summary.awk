BEGIN{
	OFS="[ <]";
	firstline = 1;
	#split("hitCache0,hitCache1,hitCache2,hitCache3,hitCache4,hitCache5", arrDesc, ",");
	split("<20us;20-50us;50-100us;100-200us;200-500us;500-1,000us;1,000-2,000us;2,000-5,000us;5,000-50,000us;>50,000us", arrTimeScope, ";");
	#split("Load Page,Make Summary");
	split("LoadPage,MakeSummary,MATCH_PHRASE_COST,SINGLE_WINDOW_COST,DOUBLE_WINDOW_COST,REPLY_time",arrPipeline,",");
}
function getmax(arg1,arg2)
{
	if((arg1+0)>(arg2+0))
	{
		return arg1;
	}
	else
		return arg2;
}
function getmin(arg1,arg2)
{
	if((arg1+0)<(arg2+0))
		return arg1;
	else
		return arg2;
}
{	
	if(match($5,/\[Sogou-Observer/)==1 && $1=="[summary_kernel:LM_INFO]")
	{
		currentline ++;		
		if(int(currentline)%5000 == 0)
			printf("%d lines completed.\n", currentline);
		split($5, temp, ",");
		gsub(/cost=/, "", temp[4]);
		gsub(/ret=/, "", temp[11]);
		if(firstline == 1)
		{
			max = temp[4];
			min = max;				
			firstline = 0;
		}
		else
		{
			max = getmax(temp[4],max);
			min = getmin(temp[4],min);
		}	
		temp[4]=temp[4]+0;		
		if(temp[4]<20)
			strDesc = 1;
		else if(temp[4]<50)
			strDesc = 2;
		else if(temp[4]<100)
			strDesc = 3;
		else if(temp[4]<200)
			strDesc = 4;
		else if(temp[4]<500)
			strDesc = 5;
		else if(temp[4]<1000)
			strDesc = 6;
		else if(temp[4]<2000)
			strDesc = 7;	
		else if(temp[4]<5000)
			strDesc = 8;	
		else if(temp[4]<50000)
			strDesc = 9;	
		else
			strDesc = 10;
			
		countScope[strDesc]++;
		count++;
		total += temp[4];
		if(temp[11] == 0)
			countRet0 ++;

	}
	if(match($7,"hit")==1 && match($5,"-Statistics-"))
	{
		temp[4]=$7;
		gsub(/\([[:space:]]+/,"(",$0);
		gsub(/hit\(/, "", temp[4]);
		gsub(/\):/, "", temp[4]);
		hit[temp[4]]++;
		
		gsub(/\(/,"",$10);
		gsub(/\)/,"",$11);
		value=($11-$10);
		if(value<20)
                        strDesc = 1;
                else if(value<50)
                        strDesc = 2;
                else if(value<100)
                        strDesc = 3;
                else if(value<200)
                        strDesc = 4;
                else if(value<500)
                        strDesc = 5;
                else if(value<1000)
                        strDesc = 6;
                else if(value<2000)
                        strDesc = 7;
                else if(value<5000)
                        strDesc = 8;
                else if(value<50000)
                        strDesc = 9;
                else
                        strDesc = 10;
		
		countMake[strDesc]++;
		all_make+=value;
	}
	
	if(match($7,"hit")==1 && match($5,"-Statistics-"))
        {
                gsub(/\([[:space:]]+/,"(",$0);
                gsub(/\(/,"",$8);
                gsub(/\)/,"",$9);
                gsub(/\(/,"",$10);
                gsub(/\)</,"",$11);
				 gsub(/>/,"",$14);
                gsub(/\(/,"",$15);
                gsub(/\),/,"",$16);

                countPipeline[1]+=($9-$8);
                countPipeline[2]+=($11-$10);
                countPipeline[3]+=$12;
                countPipeline[4]+=$13;
                countPipeline[5]+=$14;
				countPipeline[6]+=($16-$15);
        }
	
	
	
}
END{
	print "===========response time===========";
	print "avg\tmax\tmin";
	printf("%2.3fms\t%dms\t%dms\n", total/count/1000, max/1000, min/1000);
	
	print "\n=====response time percentage====="
	for(i=1; i<=10; i++)
		printf("%s:\t%2.4f%%(%d/%d)\n",arrTimeScope[i], countScope[i]/count*100, countScope[i], count);

	print "\n=====make summary time percentage====="
	    printf("make average: %2.4f\n",all_make/count);
        for(i=1; i<=10; i++)
                printf("%s:\t%2.4f%%(%d/%d)\n",arrTimeScope[i], countMake[i]/count*100, countMake[i], count);
	
	print "\n===========Pipeline time==========="
        for(i=1;i<=6;i++)
                printf("%s:\t%2.4f\n",arrPipeline[i],countPipeline[i]/count);
	
	
	print "\n========Ret=0 percentage========"
	printf("%2.4f%%(%d/%d)\n", countRet0*100/count, countRet0, count);

	print "\n========hit=1 percentage========"
	printf("%2.4f%%(%d/%d)\n", hit[1]*100/count,hit[1],count);
	
}

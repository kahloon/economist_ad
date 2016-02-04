import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import itertools
data = pd.read_csv('1454369450.csv') #read in the raw data

#only include ads with sponsors, dropping all with no sponsors listed
data = data[data.sponsor.map(lambda x: type(x) is str)]

#fix data errors in sponsor column by combining some ads erroneously split among two spellings
err_fix_dic = {"JEB 2016 (candcmte)": "Jeb 2016 (candcmte)",
              "Conservative Solutions PAC (SuperPAC), ": "Conservative Solutions PAC (SuperPAC)",
              "Keep the Promise 1 (SuperPAC)": "Keep the Promise I (SuperPAC)",
              "Marco Rubio for President": "Marco Rubio for President (candcmte)"}
for e in err_fix_dic:
    data.ix[data.sponsor==e, 'sponsor'] = err_fix_dic.get(e)

#fix this error with duplicated candidate
data.ix[data.candidate=='Kasich', 'candidate'] = 'John Kasich'

#create new columns
data['short_name']=data.sponsor.map(lambda x: x.split('(')[0].strip())
data['sponsor_type']=data.sponsor.map(lambda x: x.split('(')[1].split(')')[0])

iowa_markets = ['SUX', 'CID', 'DSM'] #spread across three media markets

#create two separate dataframes of ads with iowa and nh
iowa = data[data.market.map(lambda x: x in iowa_markets)]
nh = data[data.market=='BOS']

#match each active sponsor to their supported candidate
support_dict = {'Cruz For President (candcmte)': 'Ted Cruz',
'Marco Rubio for President (candcmte)': 'Marco Rubio',
'Bernie 2016 (candcmte)': 'Bernie Sanders',
'Right To Rise USA (SuperPAC)': 'Jeb Bush',
'Hillary for America (candcmte)': 'Hillary Clinton',
'Stand For Truth (SuperPAC)': 'Ted Cruz',
'Carson America (candcmte)': 'Ben Carson',
'Huckabee For President (candcmte)': 'Mike Huckabee',
'Rand Paul for President (candcmte)': 'Rand Paul',
'Generation Forward (SuperPAC)': "Martin O'Malley",
'New Day For America (SuperPAC)': 'John Kasich',
'America Leads (SuperPAC)': 'Chris Christie',
'Chris Christie For President Inc (candcmte)': 'Chris Christie',
'Donald J. Trump For President (candcmte)': 'Donald Trump',
'Keep the Promise I (SuperPAC)': 'Ted Cruz',
'Carly for America Cmte (SuperPAC)': 'Carly Fiorina',
'Conservative Solutions PAC (SuperPAC)': 'Marco Rubio',
'Jeb 2016 (candcmte)': 'Jeb Bush',
'Kasich For America (candcmte)': 'John Kasich',
'Courageous Conservatives PAC (SuperPAC)': 'Ted Cruz',
'Future45 (SuperPAC)': '',
'Lindsey Graham 2016 (candcmte)': 'Lindsey Graham',
'2016 Cmte (SuperPAC)': 'Ben Carson',
'American Crossroads (SuperPAC)': '',
"Pursuing America's Greatness (SuperPAC)": 'Mike Huckabee',
'American Encore Action (SuperPAC)': '',
'America Rising PAC (SuperPAC)': '',
'Priorities USA Action (SuperPAC)': 'Hillary Clinton',
"O'Malley For President (candcmte)": "Martin O'Malley",
'American Bridge 21st Century (SuperPAC)': 'Hillary Clinton',
'Priorities USA (501c)': 'Hillary Clinton',
'ESA Fund (SuperPAC)': ''}

#match each candidate to their party
cand_party_dict = {"Ted Cruz": "R",
"Marco Rubio": "R",
"Bernie Sanders": "D",
"Hillary Clinton": "D",
"Ben Carson": "R",
"Mike Huckabee": "R",
"Rand Paul": "R",
"Chris Christie": "R",
"Donald Trump": "R",
"Carly Fiorina": "R",
"Jeb Bush": "R",
"John Kasich": "R",
"Lindsey Graham": "R",
"Martin O'Malley": "D"}

#function that takes data, and turns into ad counts
def pos_neg_ads(cand_name, db):
    mentioned = db[db.candidate.map(lambda x: cand_name in x)]
    it = mentioned.iterrows()
    arr = []
    for index, row in it:
        message = row['message']
        if((row['candidate']!=cand_name)): #ie more than one mentioned.
            if(support_dict.get(row['sponsor'])==cand_name):
                message = 'pro'
            else:
                message = 'con'
        if(message=='mixed'): #some single-candidate pro messages erroneously coded as mixed
            if(support_dict.get(row['sponsor'])==cand_name):
                message = 'pro'
        arr.append(message)
    mentioned['direction'] = arr

    ad_starts = mentioned.start_time.map(lambda x: datetime.datetime.strptime(x,  "%Y-%m-%d %H:%M:%S"))
    mentioned['date'] = ad_starts.map(lambda x: x.date())

    r2 = []
    for g in mentioned.groupby('date'):
        counts = g[1].direction.value_counts()
        if('pro' in counts.index):
            if('con' in counts.index):
                r2.append([g[0], counts.get('pro'), counts.get('con')])
            else:
                r2.append([g[0], counts.get('pro'), 0])
        else:
            r2.append([g[0], 0, 0])
    if(not r2):
        print "Nothing for: " + cand_name
        return pd.DataFrame([[datetime.date(2016,1,1), 0, 0, cand_name]], columns=['date', 'pro', 'con', 'cand'])
    results = pd.DataFrame(r2, columns = ['date', 'pro', 'con'])
    results['cand'] = cand_name
    return results

iowa_negative_positive = pd.concat([pos_neg_ads(cand_name = c, db = iowa) for c in cand_party_dict if cand_party_dict.get(c)=="R"])
nh_negative_positive = pd.concat([pos_neg_ads(cand_name = c, db = nh) for c in cand_party_dict if cand_party_dict.get(c)=="R"])

#download these balances as csvs
iowa_negative_positive.to_csv('iowa_negative_positive.csv', index=False)
nh_negative_positive.to_csv('nh_negative_positive.csv', index=False)

def discount(cand_name, discount_rate, ad_data):
    cand_dat = ad_data[ad_data.cand==cand_name]
    cand_dat = cand_dat.sort('date')
    it = cand_dat.iterrows()
    pros = []
    cons = []
    for index, row in it:
        cand_dat['day_distance'] = (cand_dat.date - row['date'])/np.timedelta64(1, 'D')
        window = cand_dat[(cand_dat['day_distance'] <= 0) & (cand_dat['day_distance'] >=-6)]
        rates = np.power(1/discount_rate, window.day_distance)
        pros.append(window.pro.dot(rates)/sum(rates))
        cons.append(window.con.dot(rates)/sum(rates))
    cand_dat['discount_pro'] = pros
    cand_dat['discount_con'] = cons
    return cand_dat[['cand', 'date', 'discount_pro', 'discount_con']]

def process_regression_set(ad_data_loc, poll_data_loc, natl_data_loc = 'national_rep.csv'):
    ad_balance = pd.read_csv(ad_data_loc).dropna()
    ad_balance.date = ad_balance.date.map(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date())
    ad_balance = ad_balance[ad_balance.cand!="Kasich"] #sorry old boy
    ad_balance.cand = ad_balance.cand.map(lambda x: x.split(' ')[1]) #ie take last name only

    first_day, last_day = min(ad_balance.date), max(ad_balance.date) #bounds of our ad data
    #helper function that puts in zeroes for days when cand got no ad mentions
    def fill_rows(cand_name):
        cand_dat = ad_balance[ad_balance.cand==cand_name]
        spread = (last_day-first_day)
        rows = []
        for i in range(0, spread.days+1):
            check = first_day + datetime.timedelta(days=i)
            vals = cand_dat.date.values
            if(check not in vals):
                rows.append([check, 0, 0, cand_name])
        if(not rows): return pd.DataFrame()
        return pd.DataFrame(rows, columns = ['date', 'pro', 'con', 'cand'])
    cands = pd.unique(ad_balance.cand)
    ad_balance = ad_balance.append(pd.concat([fill_rows(c) for c in cands])).sort(['cand', 'date']).reset_index(drop=True)

    #state polls
    state_polls = pd.read_csv(poll_data_loc)
    state_polls.date = state_polls.date.map(lambda x: datetime.datetime.strptime(x.split(' 00:00:00')[0], "%Y-%m-%d").date())
    state_polls = state_polls[state_polls.cand.map(lambda x: x in cands)].sort(['cand', 'date'])
    state_polls = state_polls[state_polls.date.map(lambda x: x >=first_day-datetime.timedelta(days=7))]#take an extra week
    state_polls['rcp_state']=state_polls.rcp
    del state_polls['rcp']

    #national polls
    natl_polls = pd.read_csv(natl_data_loc)
    natl_polls.date = natl_polls.date.map(lambda x: datetime.datetime.strptime(x.split(' 00:00:00')[0], "%Y-%m-%d").date())
    natl_polls = natl_polls[natl_polls.cand.map(lambda x: x in cands)].sort(['cand', 'date'])
    natl_polls = natl_polls[natl_polls.date.map(lambda x: x >=first_day-datetime.timedelta(days=7))]
    natl_polls['rcp_natl']=natl_polls.rcp

    #merging
    state_polls = natl_polls.merge(state_polls, on=['cand', 'date'])
    state_polls['difference'] = state_polls['rcp_state']-state_polls['rcp_natl']

    #calculating week ago difference
    state_polls = state_polls[state_polls.cand.map(lambda x: x in cands)].sort(['cand', 'date'])
    state_polls['difference_before'] = state_polls.difference.shift(7)
    state_polls = state_polls[state_polls.date.map(lambda x: x>=first_day)]

    #ad discounting
    discount_balance = pd.concat([discount(c, discount_rate=1, ad_data = ad_balance) for c in cands]).reset_index(drop=True)

    regset = state_polls.merge(discount_balance)
    regset['gap'] = regset['difference'] - regset['difference_before']

    #generate candidate pairs
    gapset = []
    for index, group in regset.groupby('date'):
        group = group.reset_index(drop=True)
        for l in itertools.combinations(range(len(group)), 2):
            i,j = l
            cand1 = group.iloc[i].cand
            cand2 = group.iloc[j].cand
            poll_gap = round(group.iloc[i].gap-group.iloc[j].gap,1) #some floating point error
            pro_gap = group.iloc[i].discount_pro-group.iloc[j].discount_pro
            con_gap = group.iloc[i].discount_con-group.iloc[j].discount_con
            #must be polling 10 percent in at least national or state polls
            if(((group.iloc[i].rcp_state >= 10) | (group.iloc[i].rcp_natl >= 10))
               & ((group.iloc[j].rcp_state >= 10) | (group.iloc[j].rcp_natl >= 10))):
                gapset.append([cand1, cand2, index, poll_gap, pro_gap, con_gap])

    processed = pd.DataFrame(gapset, columns = ['cand1', 'cand2', 'week', 'poll_gap', 'pro_gap', 'con_gap']).dropna()
    return processed

piowa = process_regression_set(ad_data_loc = 'iowa_negative_positive.csv', poll_data_loc = 'iowa_rep.csv')
piowa['state']='Iowa'
pnh = process_regression_set(ad_data_loc = 'nh_negative_positive.csv', poll_data_loc = 'nh_rep.csv')
pnh['state']='New Hampshire'

#here you go. for regression in your favorite program
#to get our effect sizes for the week, remember that our pro_gap and con_gap coeffs are averaged over a week
pd.concat([piowa, pnh]).to_csv('economist_primary_data.csv', index=False)

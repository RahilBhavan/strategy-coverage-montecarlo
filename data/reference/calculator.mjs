// Same snapshot equations as Coverage/Liquidity; all money is USD millions.
export const snapshot={asOf:'2026-10-15',btc:848250,spot:82131,reserve:4880,atm:18807.6,fdso:431.0530776696268,netValue:55521.74565,baseCharges:1559.673002,strcNotional:8792.1436,baseRate:.12,mnav:1.1745671782680673,adv:22,participation:.02,tradingDays:252,displayCap:50};
export function coverage({price=snapshot.spot,mnav=snapshot.mnav,rate=snapshot.baseRate}={}){
 if(![price,mnav,rate].every(Number.isFinite)||price<=0||mnav<0||rate<0)throw Error('Enter a positive BTC price and nonnegative mNAV and rate.');
 const p=snapshot,charges=p.baseCharges+p.strcNotional*(rate-p.baseRate),net=p.netValue+p.btc*(price-p.spot)/1e6,marketCap=Math.max(0,mnav*net),sharePrice=marketCap/p.fdso;
 const annualCommon=mnav<1?0:p.adv*sharePrice*p.participation*p.tradingDays;
 const years=annualCommon<charges&&annualCommon*p.reserve/(charges-annualCommon)<=p.atm?p.reserve/(charges-annualCommon):(p.reserve+p.atm)/charges;
 return {charges,months:p.reserve/charges*12,years:Math.min(p.displayCap,years),annualCommon,sharePrice,netValue:net};
}

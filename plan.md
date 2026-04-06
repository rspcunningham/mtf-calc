
User workflow: 

1) select a .npy data file
2) select a series of ROIs in the image, and save refs to them by pixel bounding box coords. 
  - save the black square roi --> this is important for more than one reason
  - save the white square roi --> enforce same size
  - save the bar pattern rois --> need to be captured in the correct order to associate spation frequencies with them
  - (optionally, future): show agent processing the image to extract rois
3) display each bar pattern roi sequentially
  - for each, show the tensor section itself as the taylor expansion graph
  - allow the operator to select the number of coeffs and view the data to make the right choice
  - save the resulting fitted curve
4) calculate mtf at each spatial frequency based on those coeffs
5) display the resulting graph and save the actual data, perhaps as a csv

Priorities: 
 - each stage should be either deterministic or easily automatable with ai agents. 
 - end goal is end-to-end autonomy with a gui for viewing what the ai is doing to confirm. 

From dr. cunningham

Given a specific bar pattern region (ie a group of 3 bars) 
1) calculate the profile as in the image, but averages across a rectangle, not just a line
2) fit that profile to a square wave plus harmonics (probably about 5 harmonics?)
	1) for higher frequency bar patterns, 0 + 1 harmonic will be good. lower frequencies will need more harmonics. allowing too many harmonics leads to overfitting when they are not needed
	2) the operator may need to pick the best number of harmonics (you pick the fewest number of terms where you actually get a good fit)
3) the deliverable from the above is the coefficients on those terms, one set per bar pattern frequency
4) MTF is a function of those coeffs
5) we need to normalize wrt zero frequency, ie large white and large black patches. 

when the square wave is fitted, there is often issues because the data is not clean. dad added in a linear straight line (2 params, m and b) as a linear combination with the square wave, ie added together as an additional term.

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")


from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

# Define enums for string options
class VehicleType(str, Enum):
    CAR = "car"
    SUV = "suv"
    MOTORCYCLE = "motorcycle"
    NONE = "none"

class FuelType(str, Enum):
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    NONE = "none"

class DwellingType(str, Enum):
    APARTMENT = "apartment"
    TOWNHOUSE = "townhouse"
    HOUSE = "house"

class HeatingSource(str, Enum):
    NATURAL_GAS = "natural_gas"
    ELECTRICITY = "electricity"
    OIL = "oil"
    PROPANE = "propane"

class DietType(str, Enum):
    MEAT_HEAVY = "meat_heavy"
    AVERAGE = "average"
    PESCATARIAN = "pescatarian"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"

class UsageLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

class WaterUsageLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class IncomeLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Location(str, Enum):
    US = "US"
    EU = "EU"
    CA = "CA"
    CN = "CN"
    IN = "IN"
    AU = "AU"
    OTHER = "other"

# Define Pydantic models
class CarbonFootprintInput(BaseModel):
    # Transportation
    vehicle_type: VehicleType
    vehicle_fuel_type: FuelType
    miles_driven_weekly: float
    fuel_efficiency_mpg: float
    public_transit_hours_weekly: float
    flights_short_haul: int
    flights_medium_haul: int
    flights_long_haul: int
    
    # Home Energy
    home_size_sqft: float
    dwelling_type: DwellingType
    num_residents: int
    heating_source: HeatingSource
    electricity_kwh_monthly: float
    natural_gas_therms_monthly: float = 0
    fuel_oil_gallons_monthly: float = 0
    renewable_energy_percentage: float = Field(0, ge=0, le=100)
    
    # Food Choices
    diet_type: DietType
    local_food_percentage: float = Field(0, ge=0, le=100)
    food_waste_percentage: float = Field(0, ge=0, le=100)
    meals_eaten_out_weekly: int
    
    # Consumer Habits
    new_clothes_items_yearly: int
    new_electronics_items_yearly: int
    recycling_rate: float = Field(0, ge=0, le=100)
    single_use_plastic_level: UsageLevel
    water_consumption_level: WaterUsageLevel
    
    # Secondary Information
    location: Location
    income_level: IncomeLevel

class CarbonFootprintResult(BaseModel):
    total_carbon_footprint: float
    transport_emissions: float
    home_emissions: float
    food_emissions: float
    consumer_emissions: float


def calculate_carbon_footprint(input_data: CarbonFootprintInput) -> CarbonFootprintResult:
    # Initialize emissions by category
    transport_emissions = 0
    home_emissions = 0
    food_emissions = 0
    consumer_emissions = 0
    
    # --- TRANSPORTATION EMISSIONS ---
    
    # Vehicle emissions
    if input_data.vehicle_type != VehicleType.NONE:
        # Convert weekly miles to annual
        annual_miles = input_data.miles_driven_weekly * 52
        
        # Emission factors by vehicle and fuel type (kg CO2e per mile)
        vehicle_emission_factors = {
            VehicleType.CAR: {
                FuelType.GASOLINE: 0.33,
                FuelType.DIESEL: 0.31,
                FuelType.HYBRID: 0.19,
                FuelType.ELECTRIC: 0.1  # Varies by electricity grid mix
            },
            VehicleType.SUV: {
                FuelType.GASOLINE: 0.44,
                FuelType.DIESEL: 0.42,
                FuelType.HYBRID: 0.29,
                FuelType.ELECTRIC: 0.12
            },
            VehicleType.MOTORCYCLE: {
                FuelType.GASOLINE: 0.18,
                FuelType.DIESEL: 0.0,   # Not common
                FuelType.HYBRID: 0.0,   # Not common
                FuelType.ELECTRIC: 0.05
            }
        }
        
        # Adjust electric vehicle emissions based on location
        electricity_factors = {
            Location.US: 1.0,    # Baseline
            Location.EU: 0.7,    # Cleaner grid on average
            Location.CA: 0.5,    # Very clean grid
            Location.CN: 1.5,    # Coal-heavy grid
            Location.IN: 1.4,    # Coal-heavy grid
            Location.AU: 1.2     # Coal-heavy grid
        }
        
        location_factor = electricity_factors.get(input_data.location, 1.0)
        
        if input_data.vehicle_fuel_type == FuelType.ELECTRIC:
            vehicle_emission_factors[input_data.vehicle_type][FuelType.ELECTRIC] *= location_factor
        
        emission_factor = vehicle_emission_factors.get(input_data.vehicle_type, {}).get(input_data.vehicle_fuel_type, 0.33)
        transport_emissions += annual_miles * emission_factor / 1000  # Convert to metric tons
    
    # Public transit emissions
    public_transit_annual_hours = input_data.public_transit_hours_weekly * 52
    public_transit_emissions_factor = 0.05  # metric tons CO2e per 100 hours
    transport_emissions += (public_transit_annual_hours / 100) * public_transit_emissions_factor
    
    # Flight emissions
    flight_emission_factors = {
        'short': 0.15,    # metric tons CO2e per flight
        'medium': 0.4,    # metric tons CO2e per flight
        'long': 1.5       # metric tons CO2e per flight
    }
    
    transport_emissions += (input_data.flights_short_haul * flight_emission_factors['short'] +
                           input_data.flights_medium_haul * flight_emission_factors['medium'] +
                           input_data.flights_long_haul * flight_emission_factors['long'])
    
    # --- HOME ENERGY EMISSIONS ---
    
    # Adjust for number of residents (divide by number of residents)
    resident_factor = 1 / input_data.num_residents
    
    # Electricity emissions
    electricity_annual_kwh = input_data.electricity_kwh_monthly * 12
    electricity_emission_factor = {
        Location.US: 0.0004,  # metric tons CO2e per kWh
        Location.EU: 0.0003,
        Location.CA: 0.00015,
        Location.CN: 0.0007,
        Location.IN: 0.0008,
        Location.AU: 0.0007
    }.get(input_data.location, 0.0004)
    
    # Adjust for renewable energy percentage
    electricity_emissions = (electricity_annual_kwh * electricity_emission_factor * 
                           (1 - input_data.renewable_energy_percentage / 100))
    
    # Natural gas emissions
    natural_gas_annual_therms = input_data.natural_gas_therms_monthly * 12
    natural_gas_emission_factor = 0.0053  # metric tons CO2e per therm
    natural_gas_emissions = natural_gas_annual_therms * natural_gas_emission_factor
    
    # Fuel oil emissions
    fuel_oil_annual_gallons = input_data.fuel_oil_gallons_monthly * 12
    fuel_oil_emission_factor = 0.01  # metric tons CO2e per gallon
    fuel_oil_emissions = fuel_oil_annual_gallons * fuel_oil_emission_factor
    
    # Adjustments based on dwelling type and size
    home_size_factor = min(input_data.home_size_sqft / 1500, 2.0)  # Normalize to 1500 sqft baseline, cap at 2x
    
    dwelling_factor = {
        DwellingType.APARTMENT: 0.8,
        DwellingType.TOWNHOUSE: 1.0,
        DwellingType.HOUSE: 1.2
    }.get(input_data.dwelling_type, 1.0)
    
    home_emissions = (electricity_emissions + natural_gas_emissions + fuel_oil_emissions) * resident_factor * home_size_factor * dwelling_factor
    
    # --- FOOD EMISSIONS ---
    
    # Base food emissions by diet type (metric tons CO2e per year)
    diet_emission_factors = {
        DietType.MEAT_HEAVY: 2.5,
        DietType.AVERAGE: 1.9,
        DietType.PESCATARIAN: 1.7,
        DietType.VEGETARIAN: 1.4,
        DietType.VEGAN: 1.1
    }
    
    base_food_emissions = diet_emission_factors.get(input_data.diet_type, 1.9)
    
    # Adjust for locally produced food (up to 20% reduction)
    local_food_adjustment = 1 - (input_data.local_food_percentage / 100 * 0.2)
    
    # Adjust for food waste (up to 30% increase for high waste)
    food_waste_adjustment = 1 + (input_data.food_waste_percentage / 100 * 0.3)
    
    # Adjust for eating out (restaurant meals have ~20% higher footprint)
    restaurant_factor = 1 + (input_data.meals_eaten_out_weekly / 21 * 0.2)  # Assuming 21 meals per week
    
    food_emissions = base_food_emissions * local_food_adjustment * food_waste_adjustment * restaurant_factor
    
    # --- CONSUMER EMISSIONS ---
    
    # Clothing emissions
    clothing_emission_factor = 0.01  # metric tons CO2e per item
    clothing_emissions = input_data.new_clothes_items_yearly * clothing_emission_factor
    
    # Electronics emissions
    electronics_emission_factor = 0.08  # metric tons CO2e per item
    electronics_emissions = input_data.new_electronics_items_yearly * electronics_emission_factor
    
    # Recycling impact (up to 15% reduction in consumer emissions)
    recycling_factor = 1 - (input_data.recycling_rate / 100 * 0.15)
    
    # Single-use plastic impact
    plastic_factors = {
        UsageLevel.HIGH: 0.2,
        UsageLevel.MEDIUM: 0.15,
        UsageLevel.LOW: 0.1,
        UsageLevel.NONE: 0.05
    }
    plastic_emissions = plastic_factors.get(input_data.single_use_plastic_level, 0.15)
    
    # Water usage impact
    water_factors = {
        WaterUsageLevel.HIGH: 0.3,
        WaterUsageLevel.MEDIUM: 0.2,
        WaterUsageLevel.LOW: 0.1
    }
    water_emissions = water_factors.get(input_data.water_consumption_level, 0.2)
    
    # Adjust consumer emissions based on income level
    income_factors = {
        IncomeLevel.LOW: 0.7,
        IncomeLevel.MEDIUM: 1.0,
        IncomeLevel.HIGH: 1.5
    }
    income_factor = income_factors.get(input_data.income_level, 1.0)
    
    consumer_emissions = (clothing_emissions + electronics_emissions + plastic_emissions + water_emissions) * recycling_factor * income_factor
    
    # Calculate total emissions
    total_emissions = transport_emissions + home_emissions + food_emissions + consumer_emissions
    
    # Return results rounded to 2 decimal places
    return CarbonFootprintResult(
        total_carbon_footprint=round(total_emissions, 2),
        transport_emissions=round(transport_emissions, 2),
        home_emissions=round(home_emissions, 2),
        food_emissions=round(food_emissions, 2),
        consumer_emissions=round(consumer_emissions, 2),
    )


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
